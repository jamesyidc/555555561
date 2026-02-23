# 时区说明 - 27币涨跌幅追踪系统

## ⏰ 重要提示：所有时间均为北京时间（UTC+8）

### 系统时区设置

**本系统所有时间显示均为北京时间（Asia/Shanghai, UTC+8）**

包括：
- ✅ 数据采集时间戳
- ✅ 前端图表X轴时间
- ✅ API返回的时间字段
- ✅ 日志记录时间
- ✅ 文件名日期
- ✅ 所有文档中的时间说明

### 数据字段时区

每条记录包含两个时间字段：

```json
{
  "timestamp": 1771853922572,              // Unix时间戳（毫秒），UTC标准
  "beijing_time": "2026-02-23 21:38:29",  // 北京时间字符串（UTC+8）
  ...
}
```

**说明**：
- `timestamp`: Unix时间戳，全球统一，便于跨时区转换
- `beijing_time`: 北京时间字符串，直接显示，无需转换

### 前端显示

前端图表使用 `beijing_time` 字段：

```javascript
// 提取时间（HH:MM:SS格式）
const time = data.beijing_time.split(' ')[1];  // "21:38:29"
```

**X轴显示**：`00:00` 到 `23:59`（北京时间）

### 采集时间

数据采集器运行在北京时区：

```python
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
now = datetime.now(BEIJING_TZ)
```

- **采集频率**: 每1分钟
- **运行时间**: 24小时不间断
- **时区**: Asia/Shanghai (UTC+8)

### 日期切换

系统在北京时间每天 **00:00** 自动切换日期：

- 基准价格重置：北京时间 00:00
- 数据文件切换：北京时间 00:00
- 日期选择器：显示北京日期

### 示例对照

| 事件 | 北京时间 | UTC时间 | 时差 |
|------|---------|---------|------|
| 数据采集开始 | 2026-02-23 00:00:32 | 2026-02-22 16:00:32 | +8小时 |
| 当前时间 | 2026-02-23 21:38:46 | 2026-02-23 13:38:46 | +8小时 |
| 午夜切换 | 2026-02-24 00:00:00 | 2026-02-23 16:00:00 | +8小时 |

### 跨时区使用

如果您在其他时区查看系统：

**方法1：直接使用北京时间**（推荐）
- 系统已经显示北京时间，无需转换
- 所有时间标签都是北京时间

**方法2：手动转换到本地时区**
```python
from datetime import datetime, timezone, timedelta

# 北京时间 -> 您的时区
beijing_time = datetime.strptime("2026-02-23 21:38:29", "%Y-%m-%d %H:%M:%S")
beijing_tz = timezone(timedelta(hours=8))
local_tz = timezone(timedelta(hours=YOUR_OFFSET))  # 例如：-5 (EST)

beijing_dt = beijing_time.replace(tzinfo=beijing_tz)
local_dt = beijing_dt.astimezone(local_tz)
```

### 文档时区标注

本项目所有文档遵循统一标注规范：

- ✅ 明确标注"北京时间"或"UTC+8"
- ✅ 涉及时间的表格标注时区列
- ✅ 示例代码注释时区信息

### 相关配置文件

**数据采集器**: `source_code/unified_coin_change_collector.py`
```python
BEIJING_TZ = pytz.timezone('Asia/Shanghai')
```

**Flask后端**: `app.py`
```python
beijing_time = datetime.now(timezone(timedelta(hours=8)))
```

**前端显示**: `templates/coin_change_tracker.html`
```javascript
// 使用 beijing_time 字段，无需转换
const timeStr = data.beijing_time.split(' ')[1];
```

---

## 常见问题

### Q: 为什么时间戳和beijing_time字段时间不一致？

A: 这是正常的。
- `timestamp` 是 UTC 时间戳（国际标准）
- `beijing_time` 是北京时间字符串（UTC+8）
- 两者相差8小时是正确的

### Q: 我在美国/欧洲，如何查看本地时间？

A: 两种方式：
1. **推荐**：直接使用北京时间（系统已显示）
2. 自行转换：北京时间 - 时差 = 本地时间

### Q: 数据何时重置基准价格？

A: 北京时间每天 **00:00:00** 自动重置

### Q: 如何确认系统时区设置正确？

A: 检查最新数据记录：
```bash
curl "http://localhost:9002/api/coin-change-tracker/history?limit=1" | grep beijing_time
```

应该显示当前北京时间（UTC+8）

---

**版本**: v1.0  
**更新时间**: 2026-02-23 21:45 (北京时间)  
**维护**: 系统管理员
