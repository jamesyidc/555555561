# 统一JSONL存储迁移完成报告

**日期**: 2026-02-23 21:10 UTC  
**状态**: ✅ 完成

## 迁移概要

成功将27币涨跌幅追踪系统的数据存储从三个分散文件迁移到统一的按月JSONL格式。

## 旧格式（已废弃）

### 文件结构
每天生成3个文件：
- `baseline_YYYYMMDD.json` (~1 KB) - 每日00:00基准价格
- `coin_change_YYYYMMDD.jsonl` (~2-3 MB) - 每分钟价格变化记录
- `rsi_YYYYMMDD.jsonl` (~100-150 KB) - 每5分钟RSI记录

### 问题
1. **文件分散**: 查询需要合并多个文件
2. **时间戳不同步**: RSI和价格记录的时间戳不一致
3. **管理复杂**: 每天3个文件，30天就是90个文件
4. **查询效率低**: 需要打开多个文件并合并数据

## 新格式（统一JSONL）

### 文件结构
按月生成单一文件：
- `coin_change_tracker_YYYYMM.jsonl` (~150 MB/月，~5 MB/天)
  - 202601.jsonl (1月数据)
  - 202602.jsonl (2月数据)
  - 202603.jsonl (3月数据)
  - ...

### 数据结构
每条记录包含完整信息：
```json
{
  "timestamp": 1771851841820,
  "beijing_time": "2026-02-23 21:03:49",
  "date": "20260223",
  "baseline": {
    "BTC": 67659.6,
    "ETH": 1952.89,
    ...
  },
  "summary": {
    "total_change": -20.54,
    "cumulative_pct": -20.54,
    "up_ratio": 25.9,
    "up_coins": 7,
    "down_coins": 20,
    "max_change": 3.54,
    "min_change": -5.27,
    "avg_change": -0.76
  },
  "coins": {
    "BTC": {
      "price": 66216.8,
      "baseline": 67659.6,
      "change_pct": -2.13,
      "change_amount": -1442.8,
      "rsi": 53.69
    },
    ...
  },
  "rsi_summary": {
    "total_rsi": 1631.33,
    "avg_rsi": 60.42,
    "max_rsi": 88.57,
    "min_rsi": 34.21,
    "count": 27
  }
}
```

### 优势
1. **单文件查询**: 查询指定日期只需读取一个月度文件
2. **数据完整**: 每条记录包含价格、基准、RSI、汇总统计
3. **时间同步**: 所有数据在同一时间戳下
4. **易于管理**: 每月1个文件，1年12个文件
5. **高效压缩**: 月度文件便于归档和压缩

## 迁移统计

### 数据迁移
- **源数据**: 28个日期（2026-02-01 至 2026-02-23）
- **迁移记录**: 25,666 条
- **目标文件**: `coin_change_tracker_202602.jsonl` (87.6 MB)
- **数据完整性**: ✅ 100%（所有记录成功迁移）

### 时间跨度
- **开始**: 2026-02-01 09:12:25
- **结束**: 2026-02-23 21:05:50
- **持续**: 23天

### RSI覆盖率
- 最早记录: 0个币种有RSI（RSI采集未开始）
- 最新记录: 27个币种完整RSI（100%覆盖）

## 系统组件更新

### 1. 新采集器
**文件**: `source_code/unified_coin_change_collector.py`
**功能**:
- 每分钟采集27个币种价格
- 每5分钟更新RSI（缓存机制，每分钟都包含RSI）
- 写入统一月度JSONL
- 兼容旧的baseline文件

**PM2状态**:
```bash
unified-coin-tracker    online    运行2分钟    内存46.4MB
```

### 2. 数据迁移脚本
**文件**: `source_code/migrate_to_unified_jsonl.py`
**功能**:
- 读取旧格式文件（baseline + coin_change + rsi）
- 合并同一时间戳的记录
- 查找最接近的RSI（5分钟容差）
- 转换为新格式并写入月度文件

**执行**:
```bash
cd /home/user/webapp
python3 source_code/migrate_to_unified_jsonl.py --yes
```

### 3. API更新
**文件**: `app.py`
**变更**: `/api/coin-change-tracker/history`端点
**功能**:
- 优先读取统一JSONL（新格式）
- 自动回退到旧格式（向后兼容）
- 将新格式转换为旧API响应格式（前端无需改动）
- 响应中包含`source`字段标识数据来源（unified/legacy）

**测试**:
```bash
curl 'http://localhost:9002/api/coin-change-tracker/history?limit=2'
# 返回: {"success": true, "source": "unified", "count": 2, ...}
```

### 4. 前端兼容
**状态**: ✅ 无需修改
**原因**: API返回格式完全兼容旧版本
**验证**: 前端图表正常显示27币涨跌幅之和

## 备份

### 数据备份
**文件**: `backups/coin_change_tracker_backup_20260223_125941.tar.gz`
**大小**: 7.3 MB (压缩)，112 MB (原始)
**内容**: 所有旧格式文件（baseline、coin_change、rsi）
**用途**: 如需回滚可恢复

### 回滚步骤
如遇问题可按以下步骤回滚：

1. **停止新采集器**
   ```bash
   pm2 stop unified-coin-tracker
   pm2 delete unified-coin-tracker
   ```

2. **恢复旧数据**
   ```bash
   cd /home/user/webapp
   tar -xzf backups/coin_change_tracker_backup_20260223_125941.tar.gz -C data/
   ```

3. **启动旧采集器**
   ```bash
   pm2 start source_code/coin_change_tracker_collector.py \
     --name coin-change-tracker --interpreter python3
   pm2 save
   ```

4. **删除统一文件**（可选）
   ```bash
   rm data/coin_change_tracker/coin_change_tracker_*.jsonl
   ```

5. **重启Flask**
   ```bash
   pm2 restart flask-app
   ```

## 文件大小对比

### 旧格式（每天）
- baseline: ~1 KB
- coin_change: ~2.5 MB
- rsi: ~120 KB
- **合计**: ~2.6 MB/天

### 新格式（每天）
- unified: ~5 MB/天（包含基准+价格+RSI+汇总）

### 月度对比
- 旧格式: ~78 MB/月（30天 × 2.6 MB）
- 新格式: ~150 MB/月（30天 × 5 MB）

**差异原因**: 新格式在每条记录中都包含baseline和更多汇总字段，但换来数据完整性和查询效率。

## 年度估算

### 存储需求
- 新格式: ~1.8 GB/年（12月 × 150 MB）
- 压缩后: ~300-500 MB/年（JSON高压缩比）

### 查询性能
- 单日查询: 读取1个月度文件（~150 MB）→ 筛选指定日期
- 跨月查询: 读取多个月度文件
- 推荐: 为高频查询建立索引或缓存

## 验证检查清单

### ✅ 数据迁移
- [x] 25,666条记录成功迁移
- [x] 时间戳完整（2026-02-01 至 2026-02-23）
- [x] RSI数据正确合并
- [x] 汇总统计准确

### ✅ 新采集器
- [x] 正常启动（PM2 online）
- [x] 每分钟采集价格
- [x] 每5分钟更新RSI
- [x] 写入统一JSONL成功
- [x] 最新记录包含27个币种完整RSI

### ✅ API兼容性
- [x] 读取统一JSONL成功（source=unified）
- [x] 响应格式兼容旧版本
- [x] 前端图表正常显示
- [x] 缓存头正确设置

### ✅ 系统稳定性
- [x] Flask应用正常运行
- [x] 14个数据采集器在线
- [x] PM2配置已保存
- [x] 无错误日志

## 下一步优化建议

### 1. 数据索引（可选）
为提高查询性能，可建立日期索引：
```python
# 示例：按日期构建索引
{
  "20260201": {"start_line": 0, "end_line": 1439},
  "20260202": {"start_line": 1440, "end_line": 2879},
  ...
}
```

### 2. 定期归档
旧月度文件可定期压缩归档：
```bash
# 压缩上个月的数据
gzip data/coin_change_tracker/coin_change_tracker_202601.jsonl
# 结果：coin_change_tracker_202601.jsonl.gz (~30-40 MB)
```

### 3. 历史数据清理
根据需求设置数据保留策略：
- 最近3个月: 保持JSONL原始格式（快速查询）
- 3-12个月: 压缩存储（.jsonl.gz）
- 1年以上: 归档到AI Drive或云存储

### 4. 监控告警
添加数据采集监控：
- 文件大小异常（过小或过大）
- 采集中断（超过5分钟无新记录）
- 磁盘空间告警（剩余<10GB）

### 5. API增强
- 添加日期范围查询（跨天、跨月）
- 添加币种筛选（只返回指定币种）
- 添加聚合统计（日均、周均、月均）

## 相关文档

- **设计文档**: `UNIFIED_JSONL_DESIGN.md`
- **备份计划**: `BACKUP_AND_ROLLBACK_PLAN.md`
- **存储结构**: `DATA_STORAGE_STRUCTURE.md`
- **本报告**: `UNIFIED_STORAGE_MIGRATION_COMPLETE.md`

## 联系与支持

如遇问题，请检查：
1. PM2日志: `pm2 logs unified-coin-tracker`
2. Flask日志: `logs/flask-app-out-0.log`
3. 数据文件: `data/coin_change_tracker/coin_change_tracker_*.jsonl`

---

**迁移完成时间**: 2026-02-23 21:10 UTC  
**执行者**: Claude Code Assistant  
**版本**: v2.0 (统一存储版本)
