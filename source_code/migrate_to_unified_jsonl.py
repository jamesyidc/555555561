#!/usr/bin/env python3
"""
数据迁移脚本 - 将旧的三个文件格式合并到统一JSONL
Migrate from:
  - baseline_YYYYMMDD.json (每日基准价格)
  - coin_change_YYYYMMDD.jsonl (每分钟变化记录)
  - rsi_YYYYMMDD.jsonl (每5分钟RSI记录)
To:
  - coin_change_tracker_YYYYMM.jsonl (按月统一存储)
"""
import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import pytz

# 配置
DATA_DIR = Path('/home/user/webapp/data/coin_change_tracker')
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def parse_beijing_time(time_str):
    """解析北京时间字符串为时间戳"""
    try:
        dt = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        dt = BEIJING_TZ.localize(dt)
        return int(dt.timestamp() * 1000)
    except:
        return None


def load_baseline_for_date(date_str):
    """加载指定日期的基准价格"""
    baseline_file = DATA_DIR / f"baseline_{date_str}.json"
    if baseline_file.exists():
        try:
            with open(baseline_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[警告] 加载 {baseline_file.name} 失败: {e}")
    return {}


def load_rsi_for_date(date_str):
    """加载指定日期的RSI数据，按时间戳索引"""
    rsi_file = DATA_DIR / f"rsi_{date_str}.jsonl"
    rsi_by_time = {}
    
    if rsi_file.exists():
        try:
            with open(rsi_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        timestamp = record.get('timestamp')
                        if timestamp:
                            rsi_by_time[timestamp] = record
                    except json.JSONDecodeError:
                        continue
            print(f"[✓] 加载 {len(rsi_by_time)} 条RSI记录: {rsi_file.name}")
        except Exception as e:
            print(f"[警告] 加载 {rsi_file.name} 失败: {e}")
    
    return rsi_by_time


def find_closest_rsi(timestamp, rsi_by_time, tolerance_ms=300000):
    """
    查找最接近的RSI记录（5分钟容差）
    :param timestamp: 目标时间戳（毫秒）
    :param rsi_by_time: RSI数据字典 {timestamp: record}
    :param tolerance_ms: 容差（毫秒），默认5分钟=300000ms
    :return: RSI记录或None
    """
    if not rsi_by_time:
        return None
    
    # 查找最接近的时间戳
    closest_ts = min(rsi_by_time.keys(), key=lambda t: abs(t - timestamp))
    
    # 检查是否在容差范围内
    if abs(closest_ts - timestamp) <= tolerance_ms:
        return rsi_by_time[closest_ts]
    
    return None


def migrate_date(date_str, output_file, baseline=None, dry_run=False):
    """
    迁移指定日期的数据
    :param date_str: 日期字符串 YYYYMMDD
    :param output_file: 输出文件路径
    :param baseline: 基准价格字典（如果为None则自动加载）
    :param dry_run: 是否为模拟运行
    :return: 成功迁移的记录数
    """
    coin_change_file = DATA_DIR / f"coin_change_{date_str}.jsonl"
    
    if not coin_change_file.exists():
        print(f"[跳过] {date_str} - 文件不存在")
        return 0
    
    # 加载基准价格
    if baseline is None:
        baseline = load_baseline_for_date(date_str)
        if not baseline:
            print(f"[警告] {date_str} - 无基准价格，跳过")
            return 0
    
    # 加载RSI数据
    rsi_by_time = load_rsi_for_date(date_str)
    
    # 读取coin_change记录
    migrated_count = 0
    
    try:
        with open(coin_change_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    old_record = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"[错误] {coin_change_file.name} 第{line_num}行 JSON解析失败: {e}")
                    continue
                
                # 提取关键字段
                timestamp = old_record.get('timestamp')
                beijing_time = old_record.get('beijing_time')
                changes = old_record.get('changes', {})
                
                if not timestamp or not beijing_time or not changes:
                    print(f"[警告] {coin_change_file.name} 第{line_num}行 缺少关键字段")
                    continue
                
                # 构建新格式的coins字段
                coins = {}
                for symbol, change_data in changes.items():
                    current_price = change_data.get('current_price')
                    baseline_price = change_data.get('baseline_price')
                    change_pct = change_data.get('change_pct')
                    
                    if current_price is not None and baseline_price is not None:
                        coins[symbol] = {
                            'price': round(current_price, 6),
                            'baseline': round(baseline_price, 6),
                            'change_pct': round(change_pct, 2) if change_pct is not None else 0,
                            'change_amount': round(current_price - baseline_price, 6)
                        }
                
                # 计算汇总统计
                change_pcts = [c['change_pct'] for c in coins.values()]
                total_change = sum(change_pcts)
                up_coins = sum(1 for c in coins.values() if c['change_pct'] > 0)
                down_coins = len(coins) - up_coins
                up_ratio = (up_coins / len(coins) * 100) if len(coins) > 0 else 0
                
                summary = {
                    'total_change': round(total_change, 2),
                    'cumulative_pct': round(total_change, 2),
                    'up_ratio': round(up_ratio, 1),
                    'up_coins': up_coins,
                    'down_coins': down_coins,
                    'max_change': round(max(change_pcts), 2) if change_pcts else 0,
                    'min_change': round(min(change_pcts), 2) if change_pcts else 0,
                    'avg_change': round(sum(change_pcts) / len(change_pcts), 2) if change_pcts else 0
                }
                
                # 查找最接近的RSI记录
                rsi_record = find_closest_rsi(timestamp, rsi_by_time)
                
                # 如果找到RSI记录，添加到coins中
                if rsi_record and 'rsi_values' in rsi_record:
                    rsi_values = rsi_record['rsi_values']
                    for symbol in coins:
                        if symbol in rsi_values:
                            coins[symbol]['rsi'] = rsi_values[symbol]
                    
                    # 构建RSI汇总
                    rsi_list = [rsi_values[s] for s in rsi_values if s in coins]
                    if rsi_list:
                        rsi_summary = {
                            'total_rsi': round(sum(rsi_list), 2),
                            'avg_rsi': round(sum(rsi_list) / len(rsi_list), 2),
                            'max_rsi': round(max(rsi_list), 2),
                            'min_rsi': round(min(rsi_list), 2),
                            'count': len(rsi_list)
                        }
                
                # 构建新格式记录
                new_record = {
                    'timestamp': timestamp,
                    'beijing_time': beijing_time,
                    'date': date_str,
                    'baseline': baseline,
                    'summary': summary,
                    'coins': coins
                }
                
                # 如果有RSI汇总，添加到记录
                if rsi_record and 'rsi_values' in rsi_record:
                    new_record['rsi_summary'] = rsi_summary
                
                # 写入输出文件
                if not dry_run:
                    with open(output_file, 'a', encoding='utf-8') as out:
                        out.write(json.dumps(new_record, ensure_ascii=False) + '\n')
                
                migrated_count += 1
                
                # 每100条打印进度
                if migrated_count % 100 == 0:
                    print(f"  进度: {migrated_count} 条...")
        
        print(f"[✓] {date_str} - 迁移 {migrated_count} 条记录")
        return migrated_count
        
    except Exception as e:
        print(f"[错误] {date_str} 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        return 0


def main():
    """主函数"""
    print("=" * 60)
    print("数据迁移脚本 - 旧格式 → 统一JSONL")
    print("=" * 60)
    
    # 扫描所有coin_change_*.jsonl文件
    coin_change_files = sorted(DATA_DIR.glob('coin_change_*.jsonl'))
    
    if not coin_change_files:
        print("[错误] 未找到任何 coin_change_*.jsonl 文件")
        return
    
    print(f"\n[发现] {len(coin_change_files)} 个数据文件")
    
    # 按月份分组
    files_by_month = defaultdict(list)
    for f in coin_change_files:
        # 文件名格式: coin_change_20260223.jsonl
        date_str = f.stem.replace('coin_change_', '')
        if len(date_str) == 8 and date_str.isdigit():
            month_str = date_str[:6]  # 例如: 202602
            files_by_month[month_str].append(date_str)
    
    print(f"[分组] 数据跨越 {len(files_by_month)} 个月份")
    
    # 确认是否继续（支持命令行参数跳过）
    if '--yes' not in sys.argv:
        response = input("\n是否开始迁移？[y/N] ")
        if response.lower() != 'y':
            print("[取消] 迁移已取消")
            return
    else:
        print("\n[自动确认] 开始迁移...")
    
    total_migrated = 0
    
    # 按月份迁移
    for month_str in sorted(files_by_month.keys()):
        date_list = sorted(files_by_month[month_str])
        output_file = DATA_DIR / f"coin_change_tracker_{month_str}.jsonl"
        
        print(f"\n{'='*60}")
        print(f"月份: {month_str} ({len(date_list)} 天)")
        print(f"输出: {output_file.name}")
        print(f"{'='*60}")
        
        # 如果输出文件已存在，询问是否覆盖
        if output_file.exists():
            if '--yes' not in sys.argv:
                response = input(f"[警告] {output_file.name} 已存在，是否覆盖？[y/N] ")
                if response.lower() != 'y':
                    print(f"[跳过] {month_str}")
                    continue
            output_file.unlink()
            print(f"[删除] 已删除旧文件")
        
        # 迁移该月份的所有日期
        month_total = 0
        for date_str in date_list:
            count = migrate_date(date_str, output_file)
            month_total += count
        
        print(f"\n[月份汇总] {month_str} 共迁移 {month_total} 条记录")
        total_migrated += month_total
    
    print(f"\n{'='*60}")
    print(f"[完成] 迁移总计: {total_migrated} 条记录")
    print(f"{'='*60}")
    
    # 显示迁移后的文件
    unified_files = sorted(DATA_DIR.glob('coin_change_tracker_*.jsonl'))
    if unified_files:
        print(f"\n[生成文件] {len(unified_files)} 个统一JSONL文件:")
        for f in unified_files:
            file_size_mb = f.stat().st_size / (1024 * 1024)
            with open(f, 'r') as file:
                line_count = sum(1 for _ in file)
            print(f"  • {f.name} - {file_size_mb:.1f} MB ({line_count} 条记录)")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[中断] 迁移已中止")
        sys.exit(1)
