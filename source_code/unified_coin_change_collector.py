#!/usr/bin/env python3
"""
Unified Coin Change Tracker Collector - 统一币种涨跌追踪采集器
采集27个币种价格、RSI，统一存储到按月JSONL文件
版本: v2.0 - 统一存储版本
"""
import sys
sys.path.insert(0, '/home/user/webapp/source_code')

import json
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
import pytz
import numpy as np

# 配置
DATA_DIR = Path('/home/user/webapp/data/coin_change_tracker')
DATA_DIR.mkdir(parents=True, exist_ok=True)

BEIJING_TZ = pytz.timezone('Asia/Shanghai')

# 27个追踪的币种
SYMBOLS = [
    'BTC', 'ETH', 'BNB', 'XRP', 'DOGE', 
    'SOL', 'DOT', 'MATIC', 'LTC', 'LINK',
    'HBAR', 'TAO', 'CFX', 'TRX', 'TON',
    'NEAR', 'LDO', 'CRO', 'ETC', 'XLM',
    'BCH', 'UNI', 'SUI', 'FIL', 'STX',
    'CRV', 'AAVE', 'APT'
]

# RSI缓存（用于每分钟都包含RSI数据）
rsi_cache = {}
last_rsi_update = None


def get_unified_jsonl_path():
    """获取当前月份的统一JSONL文件路径"""
    now = datetime.now(BEIJING_TZ)
    month_str = now.strftime('%Y%m')  # 例如: 202602
    return DATA_DIR / f"coin_change_tracker_{month_str}.jsonl"


def calculate_rsi(prices, period=14):
    """
    计算RSI指标
    :param prices: 价格列表(从旧到新)
    :param period: RSI周期，默认14
    :return: RSI值 (0-100)
    """
    if len(prices) < period + 1:
        return None
    
    # 计算价格变化
    deltas = np.diff(prices)
    
    # 分离涨跌
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    # 计算平均涨跌
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    # 避免除零
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return round(rsi, 2)


def get_5min_candles(symbol, limit=20):
    """
    获取5分钟K线数据
    :param symbol: 币种符号
    :param limit: 获取K线数量，默认20根（足够计算RSI14）
    :return: 收盘价列表(从旧到新)
    """
    try:
        # 优先使用永续合约
        url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}-USDT-SWAP&bar=5m&limit={limit}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        # 如果永续合约失败，尝试现货
        if data.get('code') != '0' or not data.get('data'):
            url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}-USDT&bar=5m&limit={limit}"
            response = requests.get(url, timeout=5)
            data = response.json()
        
        if data.get('code') == '0' and data.get('data'):
            # K线数据格式: [时间戳, 开盘价, 最高价, 最低价, 收盘价, ...]
            # OKX返回的数据是从新到旧，需要反转
            candles = data['data']
            close_prices = [float(candle[4]) for candle in reversed(candles)]
            return close_prices
        else:
            return None
            
    except Exception as e:
        print(f"[错误] {symbol} 获取5分钟K线失败: {e}")
        return None


def get_all_rsi_values():
    """
    获取所有27个币种的RSI值
    :return: 字典 {symbol: rsi_value}
    """
    global rsi_cache, last_rsi_update
    
    rsi_values = {}
    
    for symbol in SYMBOLS:
        try:
            # 获取5分钟K线数据
            close_prices = get_5min_candles(symbol, limit=20)
            
            if close_prices and len(close_prices) >= 15:  # 至少需要15根K线来计算RSI14
                rsi = calculate_rsi(close_prices, period=14)
                if rsi is not None:
                    rsi_values[symbol] = rsi
            
            time.sleep(0.1)  # 避免请求过快
            
        except Exception as e:
            print(f"[错误] {symbol} 计算RSI失败: {e}")
            continue
    
    # 更新缓存
    if rsi_values and len(rsi_values) >= 20:  # 至少20个币种
        rsi_cache = rsi_values
        last_rsi_update = datetime.now(BEIJING_TZ)
        print(f"[RSI] 成功采集 {len(rsi_values)}/27 个币种")
    
    return rsi_values


def get_daily_open_prices():
    """从OKX获取今日开盘价（日线开盘价）"""
    try:
        open_prices = {}
        for symbol in SYMBOLS:
            try:
                # 优先使用永续合约
                url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}-USDT-SWAP&bar=1D&limit=1"
                response = requests.get(url, timeout=5)
                data = response.json()
                
                # 如果永续合约失败，尝试现货
                if data.get('code') != '0' or not data.get('data'):
                    url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}-USDT&bar=1D&limit=1"
                    response = requests.get(url, timeout=5)
                    data = response.json()
                
                if data.get('code') == '0' and data.get('data'):
                    # 日线数据格式: [时间戳, 开盘价, 最高价, 最低价, 收盘价, ...]
                    candle = data['data'][0]
                    open_price = float(candle[1])  # 开盘价
                    open_prices[symbol] = open_price
                    
                time.sleep(0.1)  # 避免请求过快
                
            except Exception as e:
                print(f"[错误] {symbol} 获取开盘价失败: {e}")
                continue
                
        return open_prices
        
    except Exception as e:
        print(f"[错误] 获取开盘价失败: {e}")
        return {}


def get_current_prices():
    """从OKX获取当前价格"""
    try:
        prices = {}
        for symbol in SYMBOLS:
            try:
                # 优先使用永续合约
                url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT-SWAP"
                response = requests.get(url, timeout=5)
                data = response.json()
                
                # 如果永续合约失败，尝试现货
                if data.get('code') != '0' or not data.get('data'):
                    url = f"https://www.okx.com/api/v5/market/ticker?instId={symbol}-USDT"
                    response = requests.get(url, timeout=5)
                    data = response.json()
                
                if data.get('code') == '0' and data.get('data'):
                    price = float(data['data'][0]['last'])
                    prices[symbol] = price
                    
                time.sleep(0.1)  # 避免请求过快
                
            except Exception as e:
                print(f"[错误] {symbol} 获取价格失败: {e}")
                continue
                
        return prices
        
    except Exception as e:
        print(f"[错误] 获取价格失败: {e}")
        return {}


def load_baseline():
    """加载基准价格（兼容旧格式）"""
    today = datetime.now(BEIJING_TZ).strftime('%Y%m%d')
    baseline_file = DATA_DIR / f"baseline_{today}.json"
    
    if baseline_file.exists():
        try:
            with open(baseline_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[错误] 加载基准价格失败: {e}")
    
    return {}


def save_baseline(prices):
    """保存基准价格（兼容旧格式）"""
    today = datetime.now(BEIJING_TZ).strftime('%Y%m%d')
    baseline_file = DATA_DIR / f"baseline_{today}.json"
    
    try:
        with open(baseline_file, 'w', encoding='utf-8') as f:
            json.dump(prices, f, indent=2, ensure_ascii=False)
        print(f"[保存] 基准价格已保存")
    except Exception as e:
        print(f"[错误] 保存基准价格失败: {e}")


def append_unified_record(record):
    """追加记录到统一JSONL文件"""
    try:
        jsonl_path = get_unified_jsonl_path()
        with open(jsonl_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        print(f"[✓] 数据已写入 {jsonl_path.name}")
    except Exception as e:
        print(f"[错误] 保存统一JSONL失败: {e}")


def main():
    """主循环"""
    print("=" * 60)
    print("统一币种涨跌追踪采集器 v2.0 启动")
    print("=" * 60)
    
    # 加载或初始化基准价格
    baseline_prices = load_baseline()
    last_baseline_date = None
    
    today = datetime.now(BEIJING_TZ).strftime('%Y%m%d')
    
    if not baseline_prices:
        print("[初始化] 获取今日开盘价作为基准...")
        baseline_prices = get_daily_open_prices()
        if baseline_prices:
            save_baseline(baseline_prices)
            last_baseline_date = today
    else:
        last_baseline_date = today
    
    # 首次启动时立即采集RSI
    print("[初始化] 首次采集RSI...")
    get_all_rsi_values()
    
    while True:
        try:
            now = datetime.now(BEIJING_TZ)
            current_date = now.strftime('%Y%m%d')
            
            # 检查是否是新的一天，重置基准价格
            if current_date != last_baseline_date:
                print(f"\n[新的一天] {current_date} - 重置基准价格...")
                baseline_prices = get_daily_open_prices()
                if baseline_prices:
                    save_baseline(baseline_prices)
                    last_baseline_date = current_date
            
            print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 开始采集...")
            
            # 获取当前价格
            current_prices = get_current_prices()
            
            # 检查是否需要更新RSI（每5分钟一次）
            should_update_rsi = False
            if last_rsi_update is None:
                should_update_rsi = True
            else:
                minutes_since_last = (now - last_rsi_update).total_seconds() / 60
                if minutes_since_last >= 5:
                    should_update_rsi = True
            
            # 更新RSI数据
            if should_update_rsi:
                print("[RSI] 开始采集5分钟RSI数据...")
                get_all_rsi_values()
            
            if current_prices and baseline_prices:
                # 计算每个币种的涨跌幅
                coins = {}
                for symbol in SYMBOLS:
                    if symbol in current_prices and symbol in baseline_prices:
                        current = current_prices[symbol]
                        baseline = baseline_prices[symbol]
                        
                        if baseline > 0:
                            change_pct = ((current - baseline) / baseline) * 100
                            change_amount = current - baseline
                            
                            coin_data = {
                                'price': round(current, 6),
                                'baseline': round(baseline, 6),
                                'change_pct': round(change_pct, 2),
                                'change_amount': round(change_amount, 6)
                            }
                            
                            # 如果有RSI缓存，添加RSI数据
                            if symbol in rsi_cache:
                                coin_data['rsi'] = rsi_cache[symbol]
                            
                            coins[symbol] = coin_data
                
                # 计算汇总统计
                change_pcts = [c['change_pct'] for c in coins.values()]
                total_change = sum(change_pcts)
                up_coins = sum(1 for c in coins.values() if c['change_pct'] > 0)
                down_coins = len(coins) - up_coins
                up_ratio = (up_coins / len(coins) * 100) if len(coins) > 0 else 0
                
                summary = {
                    'total_change': round(total_change, 2),
                    'cumulative_pct': round(total_change, 2),  # 兼容字段
                    'up_ratio': round(up_ratio, 1),
                    'up_coins': up_coins,
                    'down_coins': down_coins,
                    'max_change': round(max(change_pcts), 2) if change_pcts else 0,
                    'min_change': round(min(change_pcts), 2) if change_pcts else 0,
                    'avg_change': round(sum(change_pcts) / len(change_pcts), 2) if change_pcts else 0
                }
                
                # RSI汇总（如果有的话）
                rsi_summary = None
                if rsi_cache:
                    rsi_values = [rsi_cache[s] for s in SYMBOLS if s in rsi_cache]
                    if rsi_values:
                        rsi_summary = {
                            'total_rsi': round(sum(rsi_values), 2),
                            'avg_rsi': round(sum(rsi_values) / len(rsi_values), 2),
                            'max_rsi': round(max(rsi_values), 2),
                            'min_rsi': round(min(rsi_values), 2),
                            'count': len(rsi_values)
                        }
                
                # 构建统一记录
                record = {
                    'timestamp': int(time.time() * 1000),
                    'beijing_time': now.strftime('%Y-%m-%d %H:%M:%S'),
                    'date': current_date,
                    'baseline': baseline_prices,
                    'summary': summary,
                    'coins': coins
                }
                
                # 如果有RSI汇总，添加到记录
                if rsi_summary:
                    record['rsi_summary'] = rsi_summary
                
                # 写入统一JSONL
                append_unified_record(record)
                
                # 打印日志
                log_msg = f"[统计] 总涨跌幅: {total_change:.2f}%, 币种数: {len(coins)}, 上涨占比: {up_ratio:.1f}% ({up_coins}↑/{down_coins}↓)"
                if rsi_summary:
                    log_msg += f", RSI之和: {rsi_summary['total_rsi']}"
                print(log_msg)
            
            # 每1分钟采集一次
            print(f"[等待] 下次采集时间: {(now + timedelta(minutes=1)).strftime('%H:%M:%S')}")
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n[退出] 采集器已停止")
            break
        except Exception as e:
            print(f"[错误] 采集失败: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)


if __name__ == '__main__':
    main()
