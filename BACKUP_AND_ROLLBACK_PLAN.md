# 🔒 备份与回滚计划

## 已完成的备份

### 1. 数据备份
```
文件: backups/coin_change_tracker_backup_20260223_125941.tar.gz
大小: 7.3 MB (压缩后)
原始: 112 MB (未压缩)
内容: data/coin_change_tracker/ 目录下所有文件
日期: 2026-02-23 12:59:41 UTC
```

**包含内容**:
- ✅ 所有 baseline_*.json 文件
- ✅ 所有 coin_change_*.jsonl 文件  
- ✅ 所有 rsi_*.jsonl 文件
- ✅ 从2026-01-22 到 2026-02-23 的完整历史数据

### 2. 采集器脚本备份
```bash
# 当前运行的采集器
source_code/coin_change_tracker_collector.py
```

---

## 回滚步骤（如果新方案出问题）

### 场景1: 新采集器有问题，需要立即回滚

```bash
# 1. 停止新采集器
pm2 stop coin-change-tracker

# 2. 恢复数据（如果数据损坏）
cd /home/user/webapp
rm -rf data/coin_change_tracker/
tar -xzf backups/coin_change_tracker_backup_20260223_125941.tar.gz

# 3. 启动旧采集器
pm2 start source_code/coin_change_tracker_collector.py \
  --name coin-change-tracker \
  --interpreter python3

# 4. 保存配置
pm2 save

# 5. 验证
pm2 logs coin-change-tracker --lines 50
```

### 场景2: API修改后前端出问题

```bash
# 1. 恢复 app.py 到Git版本
cd /home/user/webapp
git checkout app.py

# 2. 重启Flask
pm2 restart flask-app

# 3. 验证
curl http://localhost:9002/api/coin-change-tracker/latest
```

### 场景3: 完全回滚到备份前状态

```bash
# 1. 停止所有服务
pm2 stop coin-change-tracker
pm2 stop flask-app

# 2. 恢复数据
cd /home/user/webapp
rm -rf data/coin_change_tracker/
tar -xzf backups/coin_change_tracker_backup_20260223_125941.tar.gz

# 3. 恢复代码（如果修改了）
git checkout source_code/coin_change_tracker_collector.py
git checkout app.py

# 4. 重启服务
pm2 start ecosystem.config.js
pm2 save

# 5. 验证
pm2 status
curl http://localhost:9002/api/coin-change-tracker/latest
```

---

## 安全实施计划

### Phase 1: 准备阶段 ✅
- [x] 备份当前数据（7.3 MB）
- [x] 创建回滚文档
- [ ] 创建新采集器代码
- [ ] 创建数据迁移脚本

### Phase 2: 测试阶段
- [ ] 在测试目录测试新采集器
- [ ] 验证数据格式正确
- [ ] 测试API读取新格式数据
- [ ] 前端验证显示正常

### Phase 3: 迁移阶段
- [ ] 停止旧采集器
- [ ] 运行数据迁移脚本
- [ ] 验证迁移后数据完整性
- [ ] 对比新旧数据条数

### Phase 4: 切换阶段
- [ ] 启动新采集器
- [ ] 监控运行10分钟
- [ ] 验证数据写入正常
- [ ] 更新API代码
- [ ] 重启Flask
- [ ] 前端验证

### Phase 5: 监控阶段
- [ ] 持续监控30分钟
- [ ] 验证数据采集无误
- [ ] 检查文件大小增长
- [ ] 前端功能验证
- [ ] 性能对比

---

## 验证清单

### 数据完整性验证
```bash
# 1. 检查记录数
wc -l data/coin_change_tracker/coin_change_20260223.jsonl
# 预期: ~950+ 条

# 2. 检查最新记录
tail -1 data/coin_change_tracker/coin_change_20260223.jsonl | python3 -m json.tool

# 3. 检查时间戳连续性
tail -5 data/coin_change_tracker/coin_change_20260223.jsonl | \
  python3 -c "import json, sys; [print(json.loads(l)['beijing_time']) for l in sys.stdin]"
```

### API功能验证
```bash
# 1. 测试最新数据API
curl -s http://localhost:9002/api/coin-change-tracker/latest | \
  python3 -c "import json, sys; d=json.load(sys.stdin); print('total_change:', d.get('total_change'))"

# 2. 测试历史数据API
curl -s "http://localhost:9002/api/coin-change-tracker/history?limit=5" | \
  python3 -c "import json, sys; d=json.load(sys.stdin); print('记录数:', len(d['data']))"

# 3. 测试RSI API
curl -s "http://localhost:9002/api/coin-change-tracker/rsi-history?limit=5" | \
  python3 -c "import json, sys; d=json.load(sys.stdin); print('RSI记录数:', len(d['data']))"
```

### 前端功能验证
```
1. 打开页面: https://9002-iqxevtl2lr766c6a5nrjk-d0b9e1e2.sandbox.novita.ai/coin-change-tracker
2. 验证蓝色折线图显示（27币涨跌幅之和）
3. 验证灰色虚线显示（RSI之和）
4. 验证自动刷新（等待30秒）
5. 验证日期切换功能
6. 验证数据详情显示
```

---

## 紧急联系信息

### 回滚决策条件

**立即回滚**（如果出现以下任一情况）:
1. ❌ 数据采集停止超过5分钟
2. ❌ API返回错误率>10%
3. ❌ 前端图表无法显示
4. ❌ 数据记录出现明显错误
5. ❌ 文件写入失败
6. ❌ PM2进程频繁重启

**继续观察**（如果出现以下情况）:
1. ⚠️ 偶尔的网络请求失败（<5%）
2. ⚠️ 单次数据采集延迟
3. ⚠️ 日志中的警告信息（非错误）

---

## 备份文件管理

### 当前备份
```
backups/coin_change_tracker_backup_20260223_125941.tar.gz
```

### 保留策略
- 本次迁移备份：**永久保留**
- 每日自动备份：保留7天
- 每周备份：保留4周
- 每月备份：保留12个月

### 恢复测试
```bash
# 定期测试备份文件可用性
mkdir -p /tmp/restore_test
cd /tmp/restore_test
tar -xzf /home/user/webapp/backups/coin_change_tracker_backup_20260223_125941.tar.gz
ls -lh data/coin_change_tracker/ | head -10
rm -rf /tmp/restore_test
```

---

## Git版本管理

### 创建备份分支
```bash
cd /home/user/webapp
git checkout -b backup-before-unified-jsonl
git add .
git commit -m "Backup before unified JSONL migration - 2026-02-23"
git checkout main  # 或 genspark_ai_developer
```

### 如果需要从Git恢复
```bash
cd /home/user/webapp
git checkout backup-before-unified-jsonl -- source_code/coin_change_tracker_collector.py
git checkout backup-before-unified-jsonl -- app.py
```

---

## 总结

### 当前状态
✅ **数据已备份**: 7.3 MB 压缩包  
✅ **回滚文档已准备**: 详细步骤已记录  
✅ **验证清单已建立**: 多层次验证  
✅ **紧急响应计划**: 清晰的决策条件  

### 下一步
准备好开始实施统一JSONL方案：
1. ✍️ 创建新采集器
2. 📝 创建迁移脚本
3. 🧪 本地测试
4. 🔄 执行迁移
5. 🚀 切换系统

**安全保障**: 随时可以在5分钟内完全回滚到当前状态！

---

**备份完成时间**: 2026-02-23 12:59:41 UTC  
**文档创建时间**: 2026-02-23 13:00:00 UTC  
**实施负责人**: AI Assistant  
**审批状态**: ✅ 已准备就绪
