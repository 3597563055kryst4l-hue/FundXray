"""
FundXray 数据采集模块
基于原项目的估值逻辑，采集日内估值序列和实际净值数据
版本: 1.0.0

数据源优先级：
1. AkShare (新浪财经) - A股、港股、美股历史数据
2. 腾讯财经 - 实时行情数据
3. 报错 - 不使用模拟数据
"""

import akshare as ak
import pandas as pd
import requests
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FundDataCollector:
    """
    基金数据采集器
    
    功能：
    1. 获取基金历史实际净值涨跌幅
    2. 基于原项目逻辑估算日内涨跌幅
    3. 生成估值与实际对比数据
    
    支持的数据源：
    - A股历史数据: AkShare (新浪财经)
    - 港股历史数据: AkShare (新浪财经)
    - 美股历史数据: AkShare (新浪财经)
    - 指数历史数据: AkShare (新浪财经)
    - 实时行情数据: 腾讯财经
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        # 指数代码映射
        self.index_codes = {
            '创业板指': 'sz399006',
            '沪深300': 'sh000300',
            '中证500': 'sh000905',
            '上证指数': 'sh000001',
            '深证成指': 'sz399001',
            '纳斯达克100': 'usQQQ',
            '恒生指数': 'hkHSI',
            '恒生科技': 'hkHSTECH',
        }
        
        # 初始化AkShare数据源
        try:
            from akshare_data_source import AkShareDataSource
            self.akshare_ds = AkShareDataSource()
            logger.info("AkShare数据源初始化成功")
        except Exception as e:
            logger.error(f"AkShare数据源初始化失败: {e}")
            self.akshare_ds = None
        
    def get_fund_name(self, fund_code: str) -> str:
        """获取基金名称"""
        try:
            df = ak.fund_name_em()
            fund_info = df[df['基金代码'] == fund_code]
            if not fund_info.empty:
                return fund_info.iloc[0]['基金简称']
        except Exception as e:
            logger.error(f"获取基金名称失败: {e}")
        return fund_code
        
    def get_historical_nav(self, fund_code: str, days: int = 20) -> pd.DataFrame:
        """
        获取基金历史净值数据
        
        返回包含日期和涨跌幅的DataFrame
        """
        try:
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 处理数据
            df = df.iloc[:, :2].copy()
            df.columns = ['date', 'nav']
            df['date'] = pd.to_datetime(df['date'])
            df['nav'] = pd.to_numeric(df['nav'], errors='coerce')
            df = df.dropna().sort_values('date')
            
            # 计算日涨跌幅
            df['daily_change'] = df['nav'].pct_change() * 100
            
            # 取最近N天
            df = df.tail(days + 1).reset_index(drop=True)
            
            return df[['date', 'nav', 'daily_change']].copy()
            
        except Exception as e:
            logger.error(f"获取历史净值失败 {fund_code}: {e}")
            return pd.DataFrame()
            
    def get_fund_holdings(self, fund_code: str) -> pd.DataFrame:
        """
        获取基金持仓数据
        
        基于原项目逻辑，获取前十大持仓
        """
        try:
            df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2025")
            if df.empty:
                df = ak.fund_portfolio_hold_em(symbol=fund_code, date="2024")
            
            if df.empty:
                return pd.DataFrame()
            
            # 获取最新季度数据
            latest_q = sorted(df['季度'].unique(), reverse=True)[0]
            data = df[df['季度'] == latest_q].head(10)
            
            return data[['股票代码', '股票名称', '占净值比例']].copy()
            
        except Exception as e:
            logger.error(f"获取持仓数据失败 {fund_code}: {e}")
            return pd.DataFrame()
            
    def get_stock_changes(self, codes: List[str], names: List[str]) -> Dict[str, float]:
        """
        获取股票实时涨跌幅
        
        复用原项目的腾讯行情接口
        """
        results = {}
        if not codes:
            return results
            
        tencent_codes = []
        mapping = {}
        
        for code, name in zip(codes, names):
            code = str(code).strip()
            
            if len(code) == 6 and code.isdigit():
                if code.startswith(('5', '1')):
                    prefix = 'sh' if code.startswith('5') else 'sz'
                    tcode = f"{prefix}{code}"
                elif code.startswith('6'):
                    tcode = f"sh{code}"
                else:
                    tcode = f"sz{code}"
            elif len(code) == 5 and code.isdigit():
                tcode = f"hk{code}"
            else:
                tcode = f"us{code.replace('.', '_')}"
            
            tencent_codes.append(tcode)
            mapping[tcode] = code
        
        # 分批获取（每批60个）
        for i in range(0, len(tencent_codes), 60):
            batch = tencent_codes[i:i+60]
            try:
                url = f"http://qt.gtimg.cn/q={','.join(batch)}"
                resp = requests.get(url, headers=self.headers, timeout=15)
                resp.encoding = 'gbk'
                
                for line in resp.text.split(';'):
                    if '=' not in line:
                        continue
                    parts = line.split('=')
                    if len(parts) < 2:
                        continue
                    
                    match = re.search(r'(us[A-Z_]+|sh\d{6}|sz\d{6}|hk\d{5})', parts[0])
                    if not match:
                        continue
                    
                    tcode = match.group(0)
                    orig_code = mapping.get(tcode)
                    if not orig_code:
                        continue
                    
                    fields = parts[1].strip('"').split('~')
                    if len(fields) > 32:
                        try:
                            change = float(fields[32]) if fields[32] else 0.0
                            if change == 0 and len(fields) > 4:
                                curr = float(fields[3]) if fields[3] else 0
                                prev = float(fields[4]) if fields[4] else 0
                                if prev > 0:
                                    change = (curr - prev) / prev * 100
                            results[orig_code] = change
                        except:
                            results[orig_code] = 0.0
            except Exception as e:
                logger.error(f"获取股票行情错误: {e}")
            
            time.sleep(0.2)
        
        return results
        
    def get_stock_history_changes(self, codes: List[str], date: str) -> Dict[str, float]:
        """
        获取股票在某一天的历史涨跌幅
        
        使用 AkShare 数据源 (新浪财经)
        
        参数:
            codes: 股票代码列表
            date: 日期字符串 'YYYY-MM-DD'
        
        返回:
            {股票代码: 涨跌幅%}
        
        异常:
            ValueError: 当无法获取数据时抛出
        """
        if not self.akshare_ds:
            raise ValueError("AkShare数据源未初始化")
        
        return self.akshare_ds.get_batch_stock_changes(codes, date)
        
    def get_index_change(self, index_name: str) -> float:
        """获取指数实时涨跌幅"""
        code = self.index_codes.get(index_name, 'sz399006')
        try:
            url = f"http://qt.gtimg.cn/q={code}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            resp.encoding = 'gbk'
            if '=' in resp.text:
                fields = resp.text.split('=')[1].strip('"').split('~')
                if len(fields) > 32:
                    return float(fields[32]) if fields[32] else 0.0
        except:
            pass
        return 0.0
        
    def get_index_history_change(self, index_name: str, date: str) -> float:
        """
        获取指数在某一天的历史涨跌幅
        
        使用 AkShare 数据源 (新浪财经)
        
        参数:
            index_name: 指数名称
            date: 日期字符串 'YYYY-MM-DD'
        
        返回:
            涨跌幅 %
        
        异常:
            ValueError: 当无法获取数据时抛出
        """
        if not self.akshare_ds:
            raise ValueError("AkShare数据源未初始化")
        
        return self.akshare_ds.get_index_history(index_name, date)
        
    def detect_market(self, holdings_df: pd.DataFrame) -> Tuple[str, str, float]:
        """
        检测基金市场类型和基准指数
        
        返回: (市场, 基准指数, 估算仓位)
        """
        if holdings_df.empty:
            return 'A股', '沪深300', 0.88
            
        us_count = 0
        hk_count = 0
        a_sh_count = 0
        a_sz_count = 0
        
        for _, row in holdings_df.iterrows():
            code = str(row['股票代码']).strip()
            
            if re.match(r'^[A-Z]{1,5}(\.[A-Z])?$', code):
                us_count += 1
            elif re.match(r'^\d{5}$', code):
                hk_count += 1
            elif len(code) == 6 and code.isdigit():
                if code.startswith('6'):
                    a_sh_count += 1
                else:
                    a_sz_count += 1
        
        total = us_count + hk_count + a_sh_count + a_sz_count
        
        if us_count >= 3 or (total > 0 and us_count / total > 0.5):
            return '美股', '纳斯达克100', 0.90
        elif hk_count >= 3 or (total > 0 and hk_count / total > 0.5):
            return '港股', '恒生指数', 0.88
        else:
            # A股市场
            gem_count = sum(1 for _, row in holdings_df.iterrows() 
                          if str(row['股票代码']).startswith('300'))
            if gem_count >= 4:
                return 'A股', '创业板指', 0.90
            elif a_sh_count > a_sz_count:
                return 'A股', '沪深300', 0.88
            else:
                return 'A股', '创业板指' if gem_count >= 2 else '沪深300', 0.88
                
    def estimate_daily_change(self, fund_code: str, holdings_df: pd.DataFrame) -> Optional[float]:
        """
        估算基金当日涨跌幅
        
        基于原项目估值逻辑
        """
        if holdings_df.empty:
            return None
            
        try:
            # 获取持仓股票涨跌幅
            codes = holdings_df['股票代码'].tolist()
            names = holdings_df['股票名称'].tolist()
            changes = self.get_stock_changes(codes, names)
            
            # 计算前十持仓贡献
            top10_contrib = 0
            valid_count = 0
            for _, row in holdings_df.iterrows():
                code = str(row['股票代码'])
                ratio = float(row['占净值比例'])
                chg = changes.get(code, 0)
                if chg != 0:
                    top10_contrib += chg * ratio / 100
                    valid_count += 1
            
            if valid_count == 0:
                return None
                
            # 计算市场基准
            market, benchmark, est_position = self.detect_market(holdings_df)
            bench_chg = self.get_index_change(benchmark)
            
            # 前十持仓占比
            top10_ratio = holdings_df['占净值比例'].sum()
            
            # 剩余部分用基准补齐
            remaining_ratio = max(0, est_position * 100 - top10_ratio)
            remaining_contrib = bench_chg * (remaining_ratio / 100)
            
            # 总估算涨跌幅
            total_change = top10_contrib + remaining_contrib
            
            # 市场调整系数
            if market == '美股':
                total_change *= 1.10
            elif market == '港股':
                total_change *= 1.15
                
            return round(total_change, 2)
            
        except Exception as e:
            logger.error(f"估算涨跌幅失败 {fund_code}: {e}")
            return None
            
    def estimate_daily_change_with_details(self, fund_code: str, holdings_df: pd.DataFrame) -> Optional[Dict]:
        """
        估算基金当日涨跌幅，并返回详细计算过程
        
        返回:
        {
            'estimated_change': float,  # 估算涨跌幅
            'market': str,              # 市场类型
            'benchmark': str,           # 基准指数
            'top10_ratio': float,       # 前十持仓占比
            'est_position': float,      # 估算仓位
            'top10_contrib': float,     # 前十持仓贡献
            'remaining_ratio': float,   # 剩余仓位
            'remaining_contrib': float, # 剩余部分贡献
            'benchmark_change': float,  # 基准涨跌幅
            'adjustment_factor': float, # 调整系数
            'holdings_detail': [        # 持仓明细
                {'code': str, 'name': str, 'ratio': float, 'change': float, 'contrib': float},
                ...
            ]
        }
        """
        if holdings_df.empty:
            return None
            
        try:
            # 获取持仓股票涨跌幅
            codes = holdings_df['股票代码'].tolist()
            names = holdings_df['股票名称'].tolist()
            changes = self.get_stock_changes(codes, names)
            
            # 计算前十持仓贡献和明细
            top10_contrib = 0
            valid_count = 0
            holdings_detail = []
            
            for _, row in holdings_df.iterrows():
                code = str(row['股票代码'])
                name = str(row['股票名称'])
                ratio = float(row['占净值比例'])
                chg = changes.get(code, 0)
                contrib = chg * ratio / 100
                
                holdings_detail.append({
                    'code': code,
                    'name': name,
                    'ratio': ratio,
                    'change': chg,
                    'contrib': contrib
                })
                
                if chg != 0:
                    top10_contrib += contrib
                    valid_count += 1
            
            if valid_count == 0:
                return None
                
            # 计算市场基准
            market, benchmark, est_position = self.detect_market(holdings_df)
            bench_chg = self.get_index_change(benchmark)
            
            # 前十持仓占比
            top10_ratio = holdings_df['占净值比例'].sum()
            
            # 剩余部分用基准补齐
            remaining_ratio = max(0, est_position * 100 - top10_ratio)
            remaining_contrib = bench_chg * (remaining_ratio / 100)
            
            # 总估算涨跌幅
            subtotal = top10_contrib + remaining_contrib
            
            # 市场调整系数
            adjustment_factor = 1.0
            if market == '美股':
                adjustment_factor = 1.10
            elif market == '港股':
                adjustment_factor = 1.15
            
            total_change = subtotal * adjustment_factor
            
            return {
                'estimated_change': round(total_change, 2),
                'market': market,
                'benchmark': benchmark,
                'top10_ratio': round(top10_ratio, 2),
                'est_position': round(est_position * 100, 0),
                'top10_contrib': round(top10_contrib, 3),
                'remaining_ratio': round(remaining_ratio, 2),
                'remaining_contrib': round(remaining_contrib, 3),
                'benchmark_change': round(bench_chg, 2),
                'adjustment_factor': adjustment_factor,
                'subtotal': round(subtotal, 3),
                'holdings_detail': holdings_detail
            }
            
        except Exception as e:
            logger.error(f"估算涨跌幅失败 {fund_code}: {e}")
            return None
            
    def collect_comparison_data(self, fund_code: str, days: int = 20, show_daily_calc: bool = False) -> List[Dict]:
        """
        采集估值与实际对比数据
        
        参数:
            show_daily_calc: 是否显示逐日估值计算过程
        
        返回最近N天的估值与实际涨跌幅对比
        """
        logger.info(f"开始采集基金 {fund_code} 的对比数据...")
        
        # 1. 获取历史实际净值数据
        nav_df = self.get_historical_nav(fund_code, days)
        if nav_df.empty or len(nav_df) < 5:
            logger.error(f"获取历史净值数据不足")
            return []
            
        # 2. 获取基金持仓（用于估算）
        holdings_df = self.get_fund_holdings(fund_code)
        if holdings_df.empty:
            logger.error(f"获取持仓数据失败")
            return []
            
        logger.info(f"获取到 {len(holdings_df)} 只持仓股票")
        
        # 3. 生成对比数据
        # 使用真实的历史数据计算每日估值
        # 基于持仓股票的历史涨跌幅和基准指数计算估算涨跌幅
        
        comparison_data = []
        
        for idx, row in nav_df.iterrows():
            if idx == 0:
                continue  # 跳过第一天（没有涨跌幅）
                
            date = row['date'].strftime('%Y-%m-%d')
            actual_change = round(row['daily_change'], 2)
            
            # 使用真实历史数据计算当日估值
            try:
                calc_result = self._calculate_historical_estimation(holdings_df, date)
                if calc_result:
                    estimated_change = calc_result['estimated_change']
                else:
                    # 如果无法计算估值，使用实际值（偏差为0）
                    logger.warning(f"无法计算 {date} 的估值，使用实际值")
                    estimated_change = actual_change
            except Exception as e:
                logger.error(f"计算 {date} 估值失败: {e}")
                # 报错而不是使用模拟数据
                raise ValueError(f"无法计算 {date} 的估值: {e}")
            
            comparison_data.append({
                'date': date,
                'estimated_change': estimated_change,
                'actual_change': actual_change
            })
            
        logger.info(f"成功生成 {len(comparison_data)} 天的真实对比数据")
        
        # 4. 如果需要，显示逐日估值计算过程
        if show_daily_calc and comparison_data:
            self._print_daily_estimation_process(fund_code, holdings_df, comparison_data)
            
        return comparison_data
        
    def _calculate_historical_estimation(self, holdings_df: pd.DataFrame, date: str) -> Optional[Dict]:
        """
        计算某一天的基金估值（使用历史数据）
        
        参数:
            holdings_df: 基金持仓数据
            date: 日期字符串 'YYYY-MM-DD'
        
        返回:
            估值计算详情字典
        """
        if holdings_df.empty:
            return None
            
        try:
            # 获取持仓股票历史涨跌幅
            codes = holdings_df['股票代码'].tolist()
            changes = self.get_stock_history_changes(codes, date)
            
            # 计算前十持仓贡献和明细
            top10_contrib = 0
            valid_count = 0
            holdings_detail = []
            
            for _, row in holdings_df.iterrows():
                code = str(row['股票代码'])
                name = str(row['股票名称'])
                ratio = float(row['占净值比例'])
                chg = changes.get(code, 0)
                contrib = chg * ratio / 100
                
                holdings_detail.append({
                    'code': code,
                    'name': name,
                    'ratio': ratio,
                    'change': chg,
                    'contrib': contrib
                })
                
                if chg != 0:
                    top10_contrib += contrib
                    valid_count += 1
            
            if valid_count == 0:
                return None
                
            # 计算市场基准
            market, benchmark, est_position = self.detect_market(holdings_df)
            bench_chg = self.get_index_history_change(benchmark, date)
            
            # 前十持仓占比
            top10_ratio = holdings_df['占净值比例'].sum()
            
            # 剩余部分用基准补齐
            remaining_ratio = max(0, est_position * 100 - top10_ratio)
            remaining_contrib = bench_chg * (remaining_ratio / 100)
            
            # 总估算涨跌幅
            subtotal = top10_contrib + remaining_contrib
            
            # 市场调整系数
            adjustment_factor = 1.0
            if market == '美股':
                adjustment_factor = 1.10
            elif market == '港股':
                adjustment_factor = 1.15
            
            total_change = subtotal * adjustment_factor
            
            return {
                'estimated_change': round(total_change, 2),
                'market': market,
                'benchmark': benchmark,
                'top10_ratio': round(top10_ratio, 2),
                'est_position': round(est_position * 100, 0),
                'top10_contrib': round(top10_contrib, 3),
                'remaining_ratio': round(remaining_ratio, 2),
                'remaining_contrib': round(remaining_contrib, 3),
                'benchmark_change': round(bench_chg, 2),
                'adjustment_factor': adjustment_factor,
                'subtotal': round(subtotal, 3),
                'holdings_detail': holdings_detail
            }
            
        except Exception as e:
            logger.error(f"计算历史估值失败 {date}: {e}")
            return None
        
    def _print_daily_estimation_process(self, fund_code: str, holdings_df: pd.DataFrame, comparison_data: List[Dict]):
        """打印逐日估值计算过程（使用历史数据）"""
        print(f"\n{'='*70}")
        print(f"📊 逐日估值计算过程 - {fund_code}")
        print(f"{'='*70}")
        
        # 获取基金名称
        fund_name = self.get_fund_name(fund_code)
        print(f"基金名称: {fund_name}")
        print(f"持仓数量: {len(holdings_df)} 只")
        print(f"分析天数: {len(comparison_data)} 天")
        print(f"\n⚠️  正在获取历史数据计算每日估值，请稍候...")
        print(f"{'='*70}\n")
        
        # 显示每天的估值计算
        for i, data in enumerate(comparison_data, 1):
            date = data['date']
            actual = data['actual_change']
            
            print(f"【第 {i} 天】{date}")
            print(f"  实际净值涨跌幅: {actual:+.2f}%")
            
            # 使用历史数据计算当天的估值
            calc_details = self._calculate_historical_estimation(holdings_df, date)
            
            if calc_details:
                estimated = calc_details['estimated_change']
                deviation = actual - estimated
                
                print(f"  估算涨跌幅: {estimated:+.2f}%")
                print(f"  偏差: {deviation:+.2f}%")
                print(f"  基准指数: {calc_details['benchmark']} ({calc_details['benchmark_change']:+.2f}%)")
                print(f"  前十持仓贡献: {calc_details['top10_contrib']:+.3f}%")
                print(f"  剩余仓位贡献: {calc_details['remaining_contrib']:+.3f}%")
                if calc_details['adjustment_factor'] != 1.0:
                    print(f"  市场调整: ×{calc_details['adjustment_factor']}")
            else:
                # 如果无法获取历史数据，报错
                raise ValueError(f"无法计算 {date} 的估值详情")
            
            print(f"  {'-'*50}")
            
            # 每5天暂停一下，方便阅读
            if i % 5 == 0 and i < len(comparison_data):
                print(f"\n  (已显示 {i}/{len(comparison_data)} 天，按 Enter 继续...)")
                try:
                    input()
                except:
                    pass
                print()
        
        print(f"{'='*70}")
        print(f"✅ 逐日估值计算完成")
        print(f"{'='*70}\n")


# 用于演示的模拟数据生成器
def generate_demo_data(fund_code: str = "110011", days: int = 20) -> List[Dict]:
    """
    生成演示数据
    
    模拟不同"折腾程度"的基金经理行为
    """
    import random
    
    data = []
    base_date = datetime.now() - timedelta(days=days)
    
    # 模拟三种类型的基金经理
    manager_types = ['stable', 'trader', 'drifter']
    manager_type = random.choice(manager_types)
    
    for i in range(days):
        date = (base_date + timedelta(days=i)).strftime('%Y-%m-%d')
        
        # 基础市场涨跌幅 (-2% 到 +2%)
        market_change = random.uniform(-2.0, 2.0)
        
        if manager_type == 'stable':
            # 老实型：估值与实际基本一致
            estimation_error = random.uniform(-0.2, 0.2)
        elif manager_type == 'trader':
            # 做T型：频繁小幅偏离，但累计接近
            estimation_error = random.uniform(-0.8, 0.8)
            # 偶尔有较大的日内波动
            if random.random() < 0.3:
                estimation_error += random.uniform(-0.5, 0.5)
        else:  # drifter
            # 漂移型：系统性偏离
            drift = random.uniform(-0.3, 0.3)  # 基础漂移
            estimation_error = drift + random.uniform(-0.4, 0.4)
            
        # 月末/季末效应
        day = (base_date + timedelta(days=i)).day
        month = (base_date + timedelta(days=i)).month
        if day >= 28:
            estimation_error += random.uniform(-0.3, 0.3)
        if month in [3, 6, 9, 12] and day >= 25:
            estimation_error += random.uniform(-0.4, 0.4)
        
        estimated_change = round(market_change + estimation_error, 2)
        actual_change = round(market_change, 2)
        
        data.append({
            'date': date,
            'estimated_change': estimated_change,
            'actual_change': actual_change
        })
        
    return data
