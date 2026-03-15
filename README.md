# 🔬 FundXray

> **让基民看清"季报是过去的照片，而我在检测经理现在的动作"**

**基金透视仪** — 通过对比日内估值序列与实际净值，量化检测基金经理的"折腾"行为

---

## 📋 Table of Contents

- [核心价值](#-核心价值)
- [技术亮点](#-技术亮点)
- [快速开始](#-快速开始)
- [算法原理](#-算法原理)
- [技术架构](#-技术架构)
- [数据链路](#-数据链路)
- [性能优化](#-性能优化)
- [输出示例](#-输出示例)
- [项目结构](#-项目结构)
- [贡献指南](#-贡献指南)
- [免责声明](#-免责声明)

---

## 💡 核心价值

FundXray 帮助投资者识别三种典型的基金经理"折腾"行为：

| 检测维度 | 识别目标 | 技术原理 |
|---------|---------|---------|
| 🎯 **尾盘突击** | 季末/月末临时调仓粉饰业绩 | 检测月末最后1-2天估值偏差的异常放大 |
| 📊 **日内做T** | 高频交易但长期收益原地踏步 | 偏差正负交替频繁 + 累计偏差≈0 + 方差大 |
| 🔄 **风格漂移** | 实际持仓与季报行业偏离 | 估值与实际出现系统性、持续性偏离 |

### 折腾指数评分体系 (0-10分)

```
0-3分  ⭐⭐⭐ 老实持有型  → 与季报基本一致，适合长期持有
3-5分  ⭐⭐   轻度操作型  → 轻微调仓痕迹，正常市场应对
5-7分  ⭐     中度折腾型  → 明显交易痕迹，关注季报变化
7-10分 ⚠️     高度折腾型  → 过度操作，可能做T或偷偷调仓
```

---

## 🚀 技术亮点

### 1. 系统偏差校准算法 ⭐ 核心创新

**问题**：估值方法本身存在固有偏差，会干扰对基金经理操作的判断

**解决方案**：
```python
# 使用历史数据（除最近5天外）计算系统偏差
historical_data = daily_data[:-5]  # 保留最近5天作为"当前"分析窗口
mean_bias = np.mean([d.raw_deviation for d in historical_data])

# 校准后偏差 = 原始偏差 - 系统偏差
calibrated_deviation = raw_deviation - mean_bias
```

**效果**：排除估值方法本身的影响，更准确反映经理的真实操作

### 2. 多源数据融合架构

| 数据源 | 用途 | 接口 |
|-------|------|------|
| **AkShare (新浪财经)** | A股/港股/美股历史行情 | `stock_zh_a_daily` / `stock_hk_daily` / `stock_us_daily` |
| **腾讯财经** | 实时行情数据 | `http://qt.gtimg.cn/q={codes}` |
| **东方财富** | 基金净值/持仓数据 | `fund_open_fund_info_em` / `fund_portfolio_hold_em` |

### 3. 智能缓存机制

```python
# 数据缓存避免重复API调用
self._cache = {}  # {cache_key: DataFrame}

def _get_cached_data(self, cache_key: str, fetch_func) -> pd.DataFrame:
    if cache_key not in self._cache:
        df = fetch_func()
        if not df.empty:
            self._cache[cache_key] = df
    return self._cache.get(cache_key, pd.DataFrame())
```

**性能提升**：~20x（避免对同一只股票的重复历史数据请求）

### 4. 跨市场支持

- ✅ A股市场（沪深主板、创业板）
- ✅ 港股市场（港股通标的）
- ✅ 美股市场（中概股、ETF）
- ✅ 多市场混合持仓基金

---

## 🚦 快速开始

### 一键启动（推荐）

```bash
# Windows 用户
run.bat

# 按提示选择：
# 1. 演示模式 - 使用模拟数据体验功能
# 2. 分析真实基金 - 输入基金代码进行分析
```

### 命令行使用

```bash
# 安装依赖
pip install -r requirements.txt

# 分析单只基金
python fundxray.py 110011           # 易方达中小盘混合
python fundxray.py 110011 --days 30 # 分析30天数据

# 显示逐日估值计算过程
python fundxray.py 110011 --show-calc

# 演示模式
python fundxray.py 110011 --demo
```

### 命令行参数

```
python fundxray.py <基金代码> [选项]

选项:
  --days N          分析天数 (默认: 20)
  --demo            使用演示数据
  --show-calc       显示逐日估值计算过程
  --no-chart        不生成图表
  --output-dir DIR  输出目录 (默认: ./output)
```

---

## 🔬 算法原理

### 估值计算逻辑

```
基金估算涨跌幅 = Σ(持仓i涨跌幅 × 持仓i占比) + 基准指数 × 剩余仓位

其中：
- 持仓数据：基金季报披露的前十大重仓股
- 实时行情：腾讯财经API获取
- 历史行情：AkShare新浪财经接口
- 基准指数：根据持仓市场自动选择（沪深300/创业板/恒生/纳指100）
```

### 折腾指数计算

#### 1. 尾盘突击度 (0-10分)

```python
# 检测月末/季末最后几天的偏差异常放大
early_avg = np.mean([d.abs_calibrated_deviation for d in early_days])
early_std = np.std([d.abs_calibrated_deviation for d in early_days])
last_max = max([d.abs_calibrated_deviation for d in last_two_days])

z_score = (last_max - early_avg) / early_std
score = f(z_score)  # 映射到0-10分
```

#### 2. 做T痕迹分 (0-10分)

```python
# 方向变化次数（正负交替）
sign_changes = sum(1 for i in range(1, n) if dev[i-1] * dev[i] < 0)
change_score = min(sign_changes / (n-1) * 4, 3.0)

# 累计偏差（应该接近0）
cumulative = abs(sum(calibrated_deviations))
cumulative_score = max(0, 3 - cumulative / (avg_return * n) * 3)

# 方差（波动性）
variance_score = min(np.var(deviations) / 0.5 * 4, 4.0)

day_trading_score = change_score + cumulative_score + variance_score
```

#### 3. 风格漂移分 (0-10分)

```python
# 一致性（同号比例）
consistency = max(positive_count, negative_count) / total_count
consistency_score = (consistency - 0.5) * 2 * 4

# 显著性（t统计量）
t_stat = abs(mean_deviation) / (std_deviation / sqrt(n))
significance_score = min(t_stat / 2 * 4, 4.0)

# 偏离幅度
magnitude_score = min(avg_abs_deviation * 2, 2.0)

style_drift_score = consistency_score + significance_score + magnitude_score
```

#### 4. 综合折腾指数

```python
zheteng_index = (
    end_of_month_score * 0.3 +   # 尾盘突击 30%
    day_trading_score * 0.4 +    # 做T痕迹 40%
    style_drift_score * 0.3      # 风格漂移 30%
)
```

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         FundXray                                │
│                    基金经理折腾指数检测系统                       │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Presentation                                          │
│  ├─ fundxray.py          命令行入口                              │
│  ├─ visualizer.py        可视化报告生成                          │
│  └─ run.bat              一键启动脚本                            │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Analysis                                              │
│  ├─ analyzer.py          核心分析引擎                            │
│  │   ├─ SystematicBias   系统偏差校准                            │
│  │   ├─ DailyDeviation   单日偏差数据                            │
│  │   └─ WeeklyMetrics    周度指标                                │
│  └─ Data Classes         数据模型                                │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Data Collection                                       │
│  ├─ data_collector.py    数据采集协调器                          │
│  ├─ FundDataCollector    基金数据收集                            │
│  └─ _calculate_historical_estimation  历史估值计算               │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Data Sources                                          │
│  ├─ akshare_data_source.py   AkShare数据源(历史行情)              │
│  │   ├─ get_a_stock_history()      A股历史                      │
│  │   ├─ get_hk_stock_history()     港股历史                      │
│  │   ├─ get_us_stock_history()     美股历史                      │
│  │   ├─ get_index_history()        指数历史                      │
│  │   └─ _get_cached_data()         缓存机制                      │
│  ├─ tencent_data_source.py   腾讯数据源(实时行情)                 │
│  ├─ sina_data_source.py      新浪数据源(备用)                     │
│  └─ yahoo_data_source.py     Yahoo数据源(备用)                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔗 数据链路

### 实时估值流程

```
用户输入基金代码
       ↓
获取基金持仓 (AkShare: fund_portfolio_hold_em)
       ↓
识别持仓市场类型 (A股/港股/美股/混合)
       ↓
获取实时行情 (腾讯财经API)
       ↓
计算持仓贡献 + 基准指数补齐
       ↓
输出估算涨跌幅
```

### 历史分析流程

```
用户输入基金代码 + 分析天数
       ↓
获取历史净值 (AkShare: fund_open_fund_info_em)
       ↓
获取基金持仓 (季报数据)
       ↓
循环每一天:
   ├─ 获取持仓股票历史行情 (AkShare: stock_*_daily)
   ├─ 获取基准指数历史行情
   ├─ 计算当日估算涨跌幅
   └─ 对比实际净值计算偏差
       ↓
系统偏差校准 (排除估值方法固有偏差)
       ↓
计算折腾指数 (尾盘突击/做T痕迹/风格漂移)
       ↓
生成分析报告 + 可视化图表
```

---

## ⚡ 性能优化

### 优化策略

| 优化点 | 实现方式 | 效果 |
|-------|---------|------|
| **数据缓存** | 内存缓存已获取的股票历史数据 | ~20x 加速 |
| **批量请求** | 腾讯API每批60个股票代码 | 减少API调用次数 |
| **延迟加载** | 按需获取数据，避免预加载 | 减少内存占用 |
| **错误降级** | 单只股票失败不影响整体计算 | 提高稳定性 |

### 缓存命中示例

```python
# 第一次获取茅台历史数据
get_a_stock_history("600519", "2024-03-01")  # API调用

# 第二次获取（同一天或其他日期）
get_a_stock_history("600519", "2024-03-02")  # 缓存命中，无API调用
```

---

## 📊 输出示例

### 控制台输出

![FundXray Report](1.png)

> 上图展示了 FundXray 的分析报告界面，包含：
> - **折腾指数**: 4.4/10 (轻度操作型)
> - **分项指标**: 尾盘突击度、做T痕迹分、风格漂移分
> - **异常交易日检测**: Z值超过阈值的异常日期
> - **每日详细数据**: 估值、实际、原始偏差、校准偏差、偏离度
> - **统计摘要**: 平均绝对偏差、最大绝对偏差
> - **投资建议**: 基于分析结果的建议

### 输出内容说明

运行后会生成详细的分析报告，包含：

1. **核心指标**
   - 折腾指数 (0-10分)
   - 评级标签 (老实持有型/轻度操作型/中度折腾型/高度折腾型)

2. **分项指标**
   - 尾盘突击度: 检测季末/月末突击调仓
   - 做T痕迹分: 检测高频交易行为
   - 风格漂移分: 检测持仓风格变化

3. **异常检测**
   - Z值超过2.0的异常交易日
   - 正向/负向异常标记

4. **每日详细数据**
   - 日期、估值涨跌幅、实际涨跌幅
   - 原始偏差、校准偏差、偏离度

5. **统计摘要**
   - 平均绝对偏差
   - 最大绝对偏差

6. **可视化图表**
   - 自动生成 `output/<基金代码>_xray.png`
   - 包含估值vs实际对比图、偏差分析图、折腾指数仪表盘

---

## 📁 项目结构

```
FundXray/
├── fundxray.py              # 命令行入口
├── analyzer.py              # 核心分析引擎
│   ├── FundXrayAnalyzer     # 主分析器
│   ├── SystematicBias       # 系统偏差模型
│   ├── DailyDeviation       # 单日偏差数据
│   └── WeeklyMetrics        # 周度指标
├── data_collector.py        # 数据采集模块
│   ├── FundDataCollector    # 数据收集器
│   └── _calculate_historical_estimation  # 历史估值计算
├── akshare_data_source.py   # AkShare数据源
│   ├── AkShareDataSource    # 主数据源类
│   └── _get_cached_data     # 缓存机制
├── tencent_data_source.py   # 腾讯数据源(实时)
├── sina_data_source.py      # 新浪数据源(备用)
├── yahoo_data_source.py     # Yahoo数据源(备用)
├── visualizer.py            # 可视化报告
├── run.bat                  # 一键启动脚本 ⭐
├── requirements.txt         # 依赖列表
└── README.md                # 本文档
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 PR！

### 开发流程

```bash
# 1. Fork 项目

# 2. 克隆到本地
git clone https://github.com/yourusername/FundXray.git

# 3. 创建分支
git checkout -b feature/your-feature

# 4. 安装开发依赖
pip install -r requirements.txt
pip install pytest black flake8

# 5. 运行测试
pytest tests/

# 6. 提交代码
black .
flake8 .
git commit -m "feat: your feature"
```

### 代码规范

- 遵循 PEP 8 规范
- 使用类型注解
- 添加 docstring 说明
- 保持测试覆盖率 > 80%

---

## ⚠️ 免责声明

1. **数据准确性**：本工具使用的数据来源于第三方金融数据接口，不保证数据的实时性和准确性
2. **投资建议**：本工具仅供学习研究使用，不构成任何投资建议
3. **投资风险**：基金投资有风险，入市需谨慎，过往业绩不代表未来表现
4. **估值偏差**：日内估值基于公开持仓数据估算，与实际净值可能存在偏差

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

<p align="center">
  Made with ❤️ by FundXray Team
</p>

<p align="center">
  ⭐ Star us on GitHub if you find this useful!
</p>
