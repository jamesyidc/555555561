# 📊 27币涨跌幅追踪系统 - 统一JSONL存储设计

## 当前问题

目前数据分散在多个文件中：
```
data/coin_change_tracker/
├── baseline_YYYYMMDD.json          # 基准价格
├── coin_change_YYYYMMDD.jsonl      # 涨跌幅数据
└── rsi_YYYYMMDD.jsonl              # RSI数据
```

**问题**：
1. 数据分散，需要读取3个文件
2. 时间戳不完全对齐（涨跌幅每分钟，RSI每5分钟）
3. 查询需要join多个文件

---

## 新设计：统一JSONL存储

### 文件结构
```
data/coin_change_tracker/
└── coin_change_tracker_unified.jsonl    # 统一存储文件
```

### 数据格式设计

每行一条完整记录，包含所有信息：

```json
{
  "timestamp": 1771851252054,
  "beijing_time": "2026-02-23 20:53:59",
  "date": "2026-02-23",
  "time": "20:53:59",
  
  // 基准价格信息
  "baseline": {
    "date": "2026-02-23",
    "prices": {
      "BTC": 67659.6,
      "ETH": 1952.89,
      "BNB": 615.4,
      "XRP": 1.3923,
      ... // 27个币种的基准价
    }
  },
  
  // 涨跌幅汇总数据
  "summary": {
    "total_change": -13.31,          // 27币涨跌幅之和
    "cumulative_pct": -13.31,        // 同上（兼容字段）
    "up_ratio": 33.3,                // 上涨占比
    "up_coins": 9,                   // 上涨币种数
    "down_coins": 18,                // 下跌币种数
    "total_coins": 27,               // 总币种数
    "max_change": 2.45,              // 最大涨幅
    "min_change": -5.71,             // 最大跌幅
    "avg_change": -0.49              // 平均涨跌幅
  },
  
  // 每个币种的详细数据
  "coins": {
    "BTC": {
      "current_price": 66316.7,
      "baseline_price": 67659.6,
      "change_pct": -1.98,
      "change_amount": -1342.9,
      "rsi": 45.23                   // RSI值（如果有）
    },
    "ETH": {
      "current_price": 1921.99,
      "baseline_price": 1952.89,
      "change_pct": -1.58,
      "change_amount": -30.9,
      "rsi": 48.67
    },
    ... // 其余25个币种
  },
  
  // RSI汇总数据（可选，每5分钟更新）
  "rsi_summary": {
    "total_rsi": 1234.56,            // RSI之和
    "avg_rsi": 45.72,                // 平均RSI
    "max_rsi": 78.45,                // 最高RSI
    "min_rsi": 23.12,                // 最低RSI
    "overbought_count": 3,           // 超买币种数（RSI>70）
    "oversold_count": 2,             // 超卖币种数（RSI<30）
    "last_updated": "2026-02-23 20:55:00"  // RSI最后更新时间
  }
}
```

---

## 优势分析

### ✅ 相比分散存储的优势

1. **数据完整性**
   - 一条记录包含所有信息
   - 不需要join多个文件
   - 时间戳完全一致

2. **查询效率**
   - 只需读取一个文件
   - 减少IO操作
   - 简化API逻辑

3. **数据一致性**
   - 原子性写入，不会出现部分数据缺失
   - 便于事务处理
   - 减少数据不同步问题

4. **易于维护**
   - 单文件管理
   - 备份恢复简单
   - 数据迁移方便

5. **扩展性好**
   - 新增字段直接添加到记录中
   - 不影响旧数据读取
   - 版本升级平滑

---

## 存储策略

### 方案A：单文件持续追加（推荐）

```
data/coin_change_tracker/
└── coin_change_tracker_unified.jsonl    # 所有历史数据
```

**优点**：
- 最简单
- 所有数据集中
- 查询历史方便

**缺点**：
- 文件会持续增长（约2-3 MB/天）
- 需要定期归档

**适用场景**：数据量不大，需要快速查询全部历史

---

### 方案B：按月分文件（推荐用于生产）

```
data/coin_change_tracker/
├── coin_change_tracker_202601.jsonl    # 1月数据
├── coin_change_tracker_202602.jsonl    # 2月数据
└── coin_change_tracker_202603.jsonl    # 3月数据
```

**优点**：
- 文件大小可控（约70-90 MB/月）
- 便于归档和清理旧数据
- 查询当月数据快速

**缺点**：
- 跨月查询需要读取多个文件

**适用场景**：生产环境，长期运行

---

### 方案C：按日期分文件（保持现状）

```
data/coin_change_tracker/
├── coin_change_tracker_20260223.jsonl
├── coin_change_tracker_20260222.jsonl
└── ...
```

**优点**：
- 文件小（2-3 MB/天）
- 按日查询最快
- 易于管理单日数据

**缺点**：
- 文件数量多
- 查询多日需要读取多个文件

**适用场景**：需要频繁按日查询

---

## 推荐方案：方案B（按月分文件）

### 文件命名
```
coin_change_tracker_YYYYMM.jsonl
```

### 实现逻辑

```python
def get_jsonl_filepath(date=None):
    """获取当前月份的JSONL文件路径"""
    if date is None:
        date = datetime.now()
    
    year_month = date.strftime('%Y%m')
    return f'data/coin_change_tracker/coin_change_tracker_{year_month}.jsonl'

def append_record(record):
    """追加一条记录到当前月份的文件"""
    filepath = get_jsonl_filepath()
    
    # 确保目录存在
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # 追加写入
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
```

---

## 数据采集器改造

### 当前采集器逻辑

```python
# 每分钟执行
1. 获取27币种当前价格
2. 计算涨跌幅
3. 写入 coin_change_YYYYMMDD.jsonl

# 每5分钟执行
1. 计算27币种RSI
2. 写入 rsi_YYYYMMDD.jsonl
```

### 新采集器逻辑

```python
# 全局变量：缓存最新的RSI数据
latest_rsi_data = {}
latest_rsi_time = None

# 每5分钟更新RSI（后台线程）
def update_rsi():
    global latest_rsi_data, latest_rsi_time
    while True:
        rsi_data = calculate_all_rsi()
        latest_rsi_data = rsi_data
        latest_rsi_time = datetime.now()
        time.sleep(300)  # 5分钟

# 每分钟采集主数据
def collect_main():
    while True:
        # 1. 获取基准价格（每天00:00更新）
        baseline = get_or_create_baseline()
        
        # 2. 获取当前价格
        current_prices = get_current_prices()
        
        # 3. 计算涨跌幅
        changes = calculate_changes(baseline, current_prices)
        
        # 4. 构建统一记录
        record = {
            'timestamp': int(time.time() * 1000),
            'beijing_time': datetime.now(tz_beijing).strftime('%Y-%m-%d %H:%M:%S'),
            'date': datetime.now(tz_beijing).strftime('%Y-%m-%d'),
            'time': datetime.now(tz_beijing).strftime('%H:%M:%S'),
            'baseline': baseline,
            'summary': calculate_summary(changes),
            'coins': changes,
            'rsi_summary': {
                'total_rsi': sum(latest_rsi_data.values()) if latest_rsi_data else None,
                'avg_rsi': sum(latest_rsi_data.values()) / 27 if latest_rsi_data else None,
                'last_updated': latest_rsi_time.strftime('%Y-%m-%d %H:%M:%S') if latest_rsi_time else None,
                **latest_rsi_data
            } if latest_rsi_data else None
        }
        
        # 5. 追加到统一JSONL
        append_record(record)
        
        time.sleep(60)  # 1分钟
```

---

## API改造

### 当前API

```python
# 读取多个文件
@app.route('/api/coin-change-tracker/history')
def get_history():
    date = request.args.get('date', today)
    
    # 读取coin_change文件
    coin_file = f'data/coin_change_tracker/coin_change_{date}.jsonl'
    coin_data = read_jsonl(coin_file)
    
    # 读取rsi文件
    rsi_file = f'data/coin_change_tracker/rsi_{date}.jsonl'
    rsi_data = read_jsonl(rsi_file)
    
    # 需要merge两个数据集
    merged_data = merge_data(coin_data, rsi_data)
    
    return jsonify(merged_data)
```

### 新API（简化）

```python
# 只需读取一个文件
@app.route('/api/coin-change-tracker/history')
def get_history():
    date = request.args.get('date', today)
    limit = request.args.get('limit', 1440, type=int)
    
    # 确定文件路径（按月）
    year_month = date[:7].replace('-', '')  # "2026-02-23" -> "202602"
    filepath = f'data/coin_change_tracker/coin_change_tracker_{year_month}.jsonl'
    
    # 读取并过滤指定日期的数据
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            if record['date'] == date:
                records.append(record)
    
    # 限制返回数量
    records = records[-limit:] if limit else records
    
    return jsonify({
        'success': True,
        'data': records,
        'count': len(records)
    })
```

---

## 迁移计划

### 第1步：创建新采集器

```bash
# 新文件：source_code/coin_change_tracker_unified.py
# 实现统一JSONL格式的采集逻辑
```

### 第2步：历史数据迁移

```python
# 脚本：migrate_to_unified_jsonl.py
def migrate_historical_data():
    """将历史数据迁移到统一格式"""
    
    # 遍历所有日期
    for date_str in get_all_dates():
        print(f'Migrating {date_str}...')
        
        # 读取旧格式数据
        coin_data = read_jsonl(f'coin_change_{date_str}.jsonl')
        rsi_data = read_jsonl(f'rsi_{date_str}.jsonl')
        baseline = read_json(f'baseline_{date_str}.json')
        
        # 转换为新格式
        unified_records = convert_to_unified(coin_data, rsi_data, baseline)
        
        # 写入新文件（按月）
        for record in unified_records:
            append_to_unified_file(record)
        
        print(f'✅ {date_str} migrated: {len(unified_records)} records')
```

### 第3步：切换采集器

```bash
# PM2停止旧采集器
pm2 stop coin-change-tracker

# PM2启动新采集器
pm2 start source_code/coin_change_tracker_unified.py \
  --name coin-change-tracker \
  --interpreter python3

pm2 save
```

### 第4步：更新API

```python
# 修改 app.py 中的相关API
# 从读取分散文件改为读取统一JSONL
```

### 第5步：前端无需改动

```javascript
// 前端API调用完全不变
fetch('/api/coin-change-tracker/history?date=2026-02-23')

// 返回数据格式保持兼容
{
  "success": true,
  "data": [
    {
      "beijing_time": "...",
      "total_change": -13.31,
      ...
    }
  ]
}
```

---

## 完整示例记录

```json
{
  "timestamp": 1771851252054,
  "beijing_time": "2026-02-23 20:53:59",
  "date": "2026-02-23",
  "time": "20:53:59",
  "baseline": {
    "date": "2026-02-23",
    "prices": {
      "BTC": 67659.6, "ETH": 1952.89, "BNB": 615.4, "XRP": 1.3923,
      "DOGE": 0.0957, "SOL": 79.75, "DOT": 1.318, "MATIC": 0.3016,
      "LTC": 53.08, "LINK": 8.531, "HBAR": 0.09793, "TAO": 312.1,
      "CFX": 0.05113, "TRX": 0.07604, "TON": 1.526, "NEAR": 0.9841,
      "LDO": 0.6661, "CRO": 0.07564, "ETC": 8.667, "XLM": 0.10679,
      "BCH": 569.0, "UNI": 3.909, "SUI": 1.3285, "FIL": 1.515,
      "STX": 0.5365, "CRV": 0.2286, "AAVE": 118.39, "APT": 0.8328
    }
  },
  "summary": {
    "total_change": -13.31,
    "cumulative_pct": -13.31,
    "up_ratio": 33.3,
    "up_coins": 9,
    "down_coins": 18,
    "total_coins": 27,
    "max_change": 2.45,
    "min_change": -5.71,
    "avg_change": -0.49
  },
  "coins": {
    "BTC": {"current_price": 66316.7, "baseline_price": 67659.6, "change_pct": -1.98, "change_amount": -1342.9, "rsi": 45.23},
    "ETH": {"current_price": 1921.99, "baseline_price": 1952.89, "change_pct": -1.58, "change_amount": -30.9, "rsi": 48.67},
    "BNB": {"current_price": 610.6, "baseline_price": 615.4, "change_pct": -0.78, "change_amount": -4.8, "rsi": 52.11},
    "XRP": {"current_price": 1.4169, "baseline_price": 1.3923, "change_pct": 1.77, "change_amount": 0.0246, "rsi": 58.34},
    "DOGE": {"current_price": 0.09642, "baseline_price": 0.0957, "change_pct": 0.75, "change_amount": 0.00072, "rsi": 55.67}
  },
  "rsi_summary": {
    "total_rsi": 1234.56,
    "avg_rsi": 45.72,
    "max_rsi": 78.45,
    "min_rsi": 23.12,
    "overbought_count": 3,
    "oversold_count": 2,
    "last_updated": "2026-02-23 20:55:00"
  }
}
```

---

## 文件大小估算

### 单条记录大小
```
基本信息: ~100 bytes
基准价格: ~500 bytes
27币详细: ~2000 bytes
RSI数据: ~800 bytes
总计: ~3.5 KB/条
```

### 存储空间
```
一天: 1440条 × 3.5KB ≈ 5 MB
一月: 5MB × 30 ≈ 150 MB
一年: 150MB × 12 ≈ 1.8 GB
```

**结论**：按月分文件，每个文件约150 MB，完全可接受。

---

## 总结

### 推荐方案：统一JSONL + 按月分文件

**文件结构**：
```
data/coin_change_tracker/
├── coin_change_tracker_202601.jsonl    (1月数据)
├── coin_change_tracker_202602.jsonl    (2月数据)
└── coin_change_tracker_202603.jsonl    (3月数据)
```

**优势**：
✅ 数据完整统一  
✅ 查询简单高效  
✅ 文件大小可控  
✅ 易于维护管理  
✅ 扩展性强  

**下一步**：
1. 创建新采集器 `coin_change_tracker_unified.py`
2. 编写迁移脚本 `migrate_to_unified_jsonl.py`
3. 测试新采集器
4. 迁移历史数据
5. 切换PM2进程
6. 更新API代码
