"""
腾讯财经数据源模块
提供股票历史数据获取功能
版本: 1.0.0
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TencentDataSource:
    """
    腾讯财经数据源
    
    提供：
    - A股历史数据
    - 港股历史数据
    - 指数历史数据
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 指数代码映射（腾讯格式）
        self.index_mapping = {
            '上证指数': 'sh000001',
            '深证成指': 'sz399001',
            '创业板指': 'sz399006',
            '沪深300': 'sh000300',
            '中证500': 'sh000905',
            '恒生指数': 'hkHSI',
            '纳斯达克100': 'usQQQ',  # 使用QQQ代替
        }
    
    def _convert_stock_code(self, code: str) -> str:
        """
        转换股票代码为腾讯格式
        
        A股: 600519 -> sh600519 / sz000858
        港股: 00700 -> hk00700
        美股: AAPL -> usAAPL
        """
        code = str(code).strip()
        
        # A股
        if len(code) == 6 and code.isdigit():
            if code.startswith('6'):
                return f"sh{code}"
            else:
                return f"sz{code}"
        
        # 港股
        elif len(code) == 5 and code.isdigit():
            return f"hk{code}"
        
        # 美股（字母代码）
        elif code.isalpha():
            return f"us{code.upper()}"
        
        return code
    
    def get_stock_history(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票历史数据
        
        参数:
            code: 股票代码
            start_date: 开始日期 'YYYY-MM-DD'
            end_date: 结束日期 'YYYY-MM-DD'
        
        返回:
            DataFrame with columns: date, open, close, high, low, volume
        """
        try:
            tencent_code = self._convert_stock_code(code)
            
            # 腾讯历史数据接口
            url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={tencent_code},day,{start_date},{end_date},1000,qfq"
            
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            
            data = resp.json()
            
            if 'data' not in data or tencent_code not in data['data']:
                logger.debug(f"腾讯: 无数据 {code}")
                return pd.DataFrame()
            
            # 获取K线数据
            klines = data['data'][tencent_code].get('qfqday', [])
            
            if not klines:
                logger.debug(f"腾讯: 空数据 {code}")
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(klines, columns=['date', 'open', 'close', 'high', 'low', 'volume'])
            df['date'] = pd.to_datetime(df['date'])
            
            # 转换数值类型
            for col in ['open', 'close', 'high', 'low']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            
            return df.sort_values('date')
            
        except Exception as e:
            logger.debug(f"腾讯: 获取 {code} 历史数据失败: {e}")
            return pd.DataFrame()
    
    def get_stock_change(self, code: str, date: str) -> float:
        """
        获取股票在某一天的涨跌幅
        
        参数:
            code: 股票代码
            date: 日期 'YYYY-MM-DD'
        
        返回:
            涨跌幅 %
        
        异常:
            ValueError: 当无法获取数据时抛出
        """
        target_date = datetime.strptime(date, '%Y-%m-%d')
        start = (target_date - timedelta(days=5)).strftime('%Y-%m-%d')
        end = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        
        df = self.get_stock_history(code, start, end)
        
        if df.empty:
            raise ValueError(f"无法获取 {code} 在 {date} 附近的历史数据")
        
        # 找到目标日期
        target_data = df[df['date'].dt.strftime('%Y-%m-%d') == date]
        
        if target_data.empty:
            available_dates = df['date'].dt.strftime('%Y-%m-%d').tolist()
            raise ValueError(f"无法获取 {code} 在 {date} 的数据，可用日期: {available_dates}")
        
        # 计算涨跌幅
        idx = target_data.index[0]
        idx_loc = df.index.get_loc(idx)
        
        if idx_loc <= 0:
            raise ValueError(f"无法计算 {code} 在 {date} 的涨跌幅（无前一日数据）")
        
        curr_close = float(target_data.iloc[0]['close'])
        prev_close = float(df.iloc[idx_loc - 1]['close'])
        
        if prev_close <= 0:
            raise ValueError(f"{code} 在 {date} 的前一日收盘价异常: {prev_close}")
        
        change_pct = (curr_close - prev_close) / prev_close * 100
        return round(change_pct, 2)
    
    def get_index_change(self, index_name: str, date: str) -> Optional[float]:
        """
        获取指数在某一天的涨跌幅
        """
        if index_name not in self.index_mapping:
            logger.debug(f"腾讯: 未知指数 {index_name}")
            return None
        
        code = self.index_mapping[index_name]
        return self.get_stock_change(code, date)
    
    def get_batch_stock_changes(self, codes: List[str], date: str) -> Dict[str, float]:
        """
        批量获取股票涨跌幅
        """
        results = {}
        
        for code in codes:
            change = self.get_stock_change(code, date)
            if change is not None:
                results[code] = change
        
        return results
    
    def test_connection(self) -> bool:
        """测试连接"""
        try:
            change = self.get_stock_change("600519", "2024-03-01")
            return change is not None
        except:
            return False


if __name__ == '__main__':
    # 测试腾讯财经数据源
    print("测试腾讯财经数据源...")
    
    tencent = TencentDataSource()
    
    # 测试连接
    if tencent.test_connection():
        print("✅ 腾讯财经连接正常")
    else:
        print("❌ 腾讯财经连接失败")
        exit(1)
    
    # 测试获取A股数据
    print("\n测试获取贵州茅台历史数据:")
    df = tencent.get_stock_history("600519", "2024-02-01", "2024-03-01")
    if not df.empty:
        print(f"✅ 获取到 {len(df)} 条数据")
        print(df.head())
    else:
        print("❌ 获取失败")
    
    # 测试获取单日涨跌幅
    print("\n测试获取贵州茅台 2024-03-01 涨跌幅:")
    change = tencent.get_stock_change("600519", "2024-03-01")
    if change is not None:
        print(f"✅ 涨跌幅: {change:+.2f}%")
    else:
        print("❌ 获取失败")
    
    # 测试获取港股数据
    print("\n测试获取腾讯控股 2024-03-01 涨跌幅:")
    change = tencent.get_stock_change("00700", "2024-03-01")
    if change is not None:
        print(f"✅ 涨跌幅: {change:+.2f}%")
    else:
        print("❌ 获取失败")
    
    # 测试获取指数数据
    print("\n测试获取上证指数 2024-03-01 涨跌幅:")
    change = tencent.get_index_change("上证指数", "2024-03-01")
    if change is not None:
        print(f"✅ 涨跌幅: {change:+.2f}%")
    else:
        print("❌ 获取失败")
