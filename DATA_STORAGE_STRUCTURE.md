# 📊 27币涨跌幅数据存储结构说明

## 存储位置
```
/home/user/webapp/data/coin_change_tracker/
```

## 文件组织方式

### 是的，按日期分文件存储！

每天生成3类文件：

```
coin_change_tracker/
├── baseline_20260223.json       # 2月23日的基准价格（每天00:00的价格）
├── coin_change_20260223.jsonl   # 2月23日的涨跌幅数据（每分钟一条）
├── rsi_20260223.jsonl           # 2月23日的RSI数据（每5分钟一条）
├── baseline_20260222.json       # 2月22日的基准价格
├── coin_change_20260222.jsonl   # 2月22日的涨跌幅数据
├── rsi_20260222.jsonl           # 2月22日的RSI数据
├── ...                          # 更早的日期
```

---

## 文件类型详解

### 1. baseline_YYYYMMDD.json
**用途**：存储每天00:00时刻的基准价格  
**格式**：JSON  
**大小**：~1 KB  
**内容示例**：
```json
{
  "BTC": 67659.6,
  "ETH": 1952.89,
  "BNB": 615.4,
  ...（27个币种）
}
```

**作用**：作为当天涨跌幅计算的参考基准。所有涨跌幅都是相对于这个基准价格计算的。

---

### 2. coin_change_YYYYMMDD.jsonl
**用途**：存储当天每分钟的27币涨跌幅数据  
**格式**：JSONL（每行一个JSON对象）  
**大小**：~2-3 MB/天  
**更新频率**：每1分钟新增一条记录  
**每天记录数**：~1440条（24小时 × 60分钟）

**内容示例**（每行一条）：
```json
{
  "timestamp": 1771851252054,
  "beijing_time": "2026-02-23 20:53:59",
  "cumulative_pct": -13.31,      // 涨跌幅之和（主要字段）
  "total_change": -13.31,        // 同上（兼容字段）
  "up_ratio": 33.3,              // 上涨占比 33.3%
  "up_coins": 9,                 // 上涨币种数
  "down_coins": 18,              // 下跌币种数
  "count": 27,                   // 总币种数
  "changes": {                   // 每个币种的详细数据
    "BTC": {
      "current_price": 66316.7,
      "baseline_price": 67659.6,
      "change_pct": -1.98
    },
    "ETH": {
      "current_price": 1921.99,
      "baseline_price": 1952.89,
      "change_pct": -1.58
    },
    ... // 其余25个币种
  }
}
```

**重要字段说明**：
- `cumulative_pct` / `total_change`：**27币涨跌幅之和**（图表蓝色折线的数据来源）
- `up_ratio`：上涨币种占比（例如：9/27 = 33.3%）
- `changes`：每个币种的详细涨跌数据

---

### 3. rsi_YYYYMMDD.jsonl
**用途**：存储当天每5分钟的RSI指标数据  
**格式**：JSONL  
**大小**：~100-150 KB/天  
**更新频率**：每5分钟新增一条记录  
**每天记录数**：~288条（24小时 × 60分钟 ÷ 5）

**内容示例**：
```json
{
  "timestamp": 1771851315628,
  "beijing_time": "2026-02-23 20:55:15",
  "rsi_values": {
    "BTC": 45.23,
    "ETH": 48.67,
    "BNB": 52.11,
    ... // 27个币种的RSI值
  },
  "total_rsi": 1234.56,         // 27个RSI值之和
  "count": 27                   // 成功计算RSI的币种数
}
```

**重要字段说明**：
- `total_rsi`：**RSI之和**（图表灰色虚线的数据来源）
- `rsi_values`：每个币种的RSI值（14周期）

---

## 数据统计

### 当前存储情况（2026-02-23）

| 日期 | coin_change文件 | rsi文件 | 记录数 |
|------|----------------|---------|--------|
| 2月23日 | 2.3 MB | 116 KB | 950条 |
| 2月22日 | 2.6 MB | 134 KB | ~1440条 |
| 2月21日 | 2.5 MB | 129 KB | ~1440条 |
| 2月20日 | 2.8 MB | 130 KB | ~1440条 |
| ... | ... | ... | ... |

**总数据量**：约 ~3 GB（包含所有历史数据）

---

## 前端如何读取数据

### API端点
```javascript
// 获取指定日期的历史数据
GET /api/coin-change-tracker/history?date=2026-02-23&limit=1440

// 获取指定日期的RSI数据
GET /api/coin-change-tracker/rsi-history?date=2026-02-23&limit=1440
```

### 数据流程
```
1. 用户在页面选择日期（例如：2月23日）
   ↓
2. 前端调用API：/api/coin-change-tracker/history?date=2026-02-23
   ↓
3. Flask读取：data/coin_change_tracker/coin_change_20260223.jsonl
   ↓
4. 返回JSON数组：[{...}, {...}, ...] 共950条记录
   ↓
5. 前端提取：const changes = data.map(d => d.total_change)
   ↓
6. ECharts渲染蓝色折线图
```

---

## 数据采集逻辑

### 采集器：coin_change_tracker_collector.py

**运行方式**：PM2守护进程，持续运行  
**工作流程**：

```python
每天00:00:
  1. 获取27币种的现价
  2. 保存为 baseline_YYYYMMDD.json
  3. 作为当天的基准价格

每分钟（00秒时刻）：
  1. 获取27币种的当前价格
  2. 计算相对基准价格的涨跌幅
  3. 求和得到 total_change（27币涨跌幅之和）
  4. 计算 up_ratio（上涨占比）
  5. 追加一行到 coin_change_YYYYMMDD.jsonl

每5分钟：
  1. 获取27币种最近14根5分钟K线
  2. 计算每个币种的RSI(14)
  3. 求和得到 total_rsi
  4. 追加一行到 rsi_YYYYMMDD.jsonl
```

---

## 优势与特点

### ✅ 按日期分文件的优点

1. **查询高效**：
   - 只需读取指定日期的文件
   - 不需要扫描整个数据库
   - 文件大小适中（2-3 MB），快速加载

2. **存储清晰**：
   - 一天一个文件，结构清晰
   - 易于备份、迁移、删除旧数据
   - 可以单独压缩历史文件

3. **容错性好**：
   - 某天数据损坏不影响其他天
   - 可以单独修复或重新采集某天数据
   - 日志和数据一一对应

4. **扩展性强**：
   - 可以并行读取多天数据
   - 可以按需加载（不访问不加载）
   - 存储空间线性增长

---

## 数据查看示例

### 查看今天有多少条记录
```bash
wc -l data/coin_change_tracker/coin_change_20260223.jsonl
# 输出：950 条
```

### 查看最新一条记录
```bash
tail -1 data/coin_change_tracker/coin_change_20260223.jsonl | python3 -m json.tool
```

### 查看今天的基准价格
```bash
cat data/coin_change_tracker/baseline_20260223.json | python3 -m json.tool
```

### 统计某天的数据量
```bash
du -h data/coin_change_tracker/*20260223*
# 输出：
# 2.3M  coin_change_20260223.jsonl
# 116K  rsi_20260223.jsonl
```

---

## 数据备份建议

### 重要数据目录
```
/home/user/webapp/data/coin_change_tracker/
```

### 备份命令
```bash
# 备份今天的数据
tar -czf coin_change_backup_$(date +%Y%m%d).tar.gz \
  data/coin_change_tracker/coin_change_$(date +%Y%m%d).jsonl \
  data/coin_change_tracker/rsi_$(date +%Y%m%d).jsonl \
  data/coin_change_tracker/baseline_$(date +%Y%m%d).json

# 备份最近7天
tar -czf coin_change_last7days_$(date +%Y%m%d).tar.gz \
  data/coin_change_tracker/coin_change_202602*.jsonl \
  data/coin_change_tracker/rsi_202602*.jsonl

# 备份整个目录
tar -czf coin_change_full_backup_$(date +%Y%m%d).tar.gz \
  data/coin_change_tracker/
```

---

## 常见问题

### Q1: 为什么今天的记录数少于1440？
**A**: 因为今天还没结束。例如现在是20:53，所以只有从00:00到20:53的约950条记录。

### Q2: 如果采集器中断了怎么办？
**A**: 会有数据缺失。当天的JSONL文件会缺少那段时间的记录。可以通过查看时间戳判断缺失范围。

### Q3: 历史数据会自动清理吗？
**A**: 不会。所有历史数据都会保留。如需清理，可手动删除旧文件。

### Q4: 数据文件损坏了怎么办？
**A**: 
- JSONL格式容错性好，单行损坏不影响其他行
- 可以用文本编辑器修复或删除损坏行
- 或者重新运行采集器补充数据（如果行情数据还可用）

---

## 总结

✅ **按日期分文件存储**  
✅ **一天一个文件，结构清晰**  
✅ **每分钟更新，实时追加**  
✅ **JSONL格式，易于解析**  
✅ **27币涨跌幅之和存储在 `total_change` 字段**  
✅ **支持历史查询，按日期读取**

这种存储结构既保证了查询效率，又便于数据管理和备份！
