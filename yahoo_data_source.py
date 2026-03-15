"""
Yahoo Finance 数据源模块
作为 akshare 的备选数据源
版本: 1.0.0
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YahooDataSource:
    """
    Yahoo Finance 数据源
    
    支持：
    - A股（通过后缀 .SS/.SZ）
    - 港股（通过后缀 .HK）
    - 美股（直接代码）
    - 指数（通过 ^ 前缀）
    """
    
    def __init__(self):
        self.index_mapping = {
            '沪深300': '^GSPC',  # 使用标普500代替，或需要找到正确的Yahoo代码
            '创业板指': '399006.SZ',
            '上证指数': '000001.SS',
            '深证成指': '399001.SZ',
            '恒生指数': '^HSI',
            '纳斯达克100': '^NDX',
            '标普500': '^GSPC',
        }
    
    def _convert_stock_code(self, code: str) -> str:
        """
        转换股票代码为 Yahoo Finance 格式
        
        A股: 600519 -> 600519.SS (上海) / 000858.SZ (深圳)
        港股: 00700 -> 0700.HK
        美股: AAPL -> AAPL
        """
        code = str(code).strip()
        
        # A股
        if len(code) == 6 and code.isdigit():
            if code.startswith('6'):
                return f"{code}.SS"
            else:
                return f"{code}.SZ"
        
        # 港股
        elif len(code) == 5 and code.isdigit():
            return f"{code}.HK"
        
        # 美股或其他
        return code
    
    def get_stock_history(self, code: str, date: str) -> Optional[float]:
        """
        获取股票在某一天的历史涨跌幅
        
        参数:
            code: 股票代码
            date: 日期 'YYYY-MM-DD'
        
        返回:
            涨跌幅 %，失败返回 None
        """
        try:
            yahoo_code = self._convert_stock_code(code)
            
            # 计算日期范围
            target_date = datetime.strptime(date, '%Y-%m-%d')
            start = (target_date - timedelta(days=5)).strftime('%Y-%m-%d')
            end = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 获取数据
            ticker = yf.Ticker(yahoo_code)
            df = ticker.history(start=start, end=end)
            
            if df.empty:
                logger.debug(f"Yahoo: 无数据 {code} ({yahoo_code}) {date}")
                return None
            
            # 找到目标日期
            df.index = df.index.tz_localize(None)
            target_data = df[df.index.strftime('%Y-%m-%d') == date]
            
            if target_data.empty:
                logger.debug(f"Yahoo: 未找到 {code} {date}")
                return None
            
            # 计算涨跌幅
            idx = target_data.index[0]
            idx_loc = df.index.get_loc(idx)
            
            if idx_loc > 0:
                curr_close = float(target_data.iloc[0]['Close'])
                prev_close = float(df.iloc[idx_loc - 1]['Close'])
                
                if prev_close > 0:
                    change_pct = (curr_close - prev_close) / prev_close * 100
                    return round(change_pct, 2)
            
            return None
            
        except Exception as e:
            logger.debug(f"Yahoo: 获取 {code} 历史数据失败: {e}")
            return None
    
    def get_index_history(self, index_name: str, date: str) -> Optional[float]:
        """
        获取指数在某一天的历史涨跌幅
        """
        try:
            if index_name not in self.index_mapping:
                logger.debug(f"Yahoo: 未知指数 {index_name}")
                return None
            
            yahoo_code = self.index_mapping[index_name]
            
            # 计算日期范围
            target_date = datetime.strptime(date, '%Y-%m-%d')
            start = (target_date - timedelta(days=5)).strftime('%Y-%m-%d')
            end = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # 获取数据
            ticker = yf.Ticker(yahoo_code)
            df = ticker.history(start=start, end=end)
            
            if df.empty:
                logger.debug(f"Yahoo: 无数据 {index_name} ({yahoo_code}) {date}")
                return None
            
            # 找到目标日期
            df.index = df.index.tz_localize(None)
            target_data = df[df.index.strftime('%Y-%m-%d') == date]
            
            if target_data.empty:
                logger.debug(f"Yahoo: 未找到 {index_name} {date}")
                return None
            
            # 计算涨跌幅
            idx = target_data.index[0]
            idx_loc = df.index.get_loc(idx)
            
            if idx_loc > 0:
                curr_close = float(target_data.iloc[0]['Close'])
                prev_close = float(df.iloc[idx_loc - 1]['Close'])
                
                if prev_close > 0:
                    change_pct = (curr_close - prev_close) / prev_close * 100
                    return round(change_pct, 2)
            
            return None
            
        except Exception as e:
            logger.debug(f"Yahoo: 获取指数 {index_name} 历史数据失败: {e}")
            return None
    
    def get_batch_stock_history(self, codes: List[str], date: str) -> Dict[str, float]:
        """
        批量获取股票历史涨跌幅
        
        参数:
            codes: 股票代码列表
            date: 日期 'YYYY-MM-DD'
        
        返回:
            {股票代码: 涨跌幅%}
        """
        results = {}
        
        for code in codes:
            change = self.get_stock_history(code, date)
            if change is not None:
                results[code] = change
        
        return results
    
    def test_connection(self) -> bool:
        """测试 Yahoo Finance 连接"""
        try:
            # 测试获取苹果股票数据
            ticker = yf.Ticker("AAPL")
            df = ticker.history(period="5d")
            return not df.empty
        except:
            return False


# 备用：使用新浪财经获取A股历史数据
class SinaDataSource:
    """
    新浪财经数据源
    作为 akshare 和 yfinance 的备选
    """
    
    def __init__(self):
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_stock_history(self, code: str, date: str) -> Optional[float]:
        """
        从新浪财经获取股票历史数据
        """
        try:
            # 转换代码格式
            code = str(code).strip()
            if len(code) == 6 and code.isdigit():
                if code.startswith('6'):
                    sina_code = f"sh{code}"
                else:
                    sina_code = f"sz{code}"
            else:
                return None
            
            # 新浪财经历史数据接口
            url = f"https://quotes.sina.cn/cn/api/quotes.php?symbol={sina_code}"
            
            resp = self.session.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            
            # 解析数据（这里需要根据实际情况调整）
            # 新浪财经接口比较复杂，可能需要使用其他方式
            
            return None
            
        except Exception as e:
            logger.debug(f"Sina: 获取 {code} 失败: {e}")
            return None


if __name__ == '__main__':
    # 测试 Yahoo Finance 数据源
    print("测试 Yahoo Finance 数据源...")
    
    yahoo = YahooDataSource()
    
    # 测试连接
    if yahoo.test_connection():
        print("✅ Yahoo Finance 连接正常")
    else:
        print("❌ Yahoo Finance 连接失败")
        exit(1)
    
    # 测试获取A股数据
    print("\n测试获取贵州茅台 2024-03-01 数据:")
    change = yahoo.get_stock_history("600519", "2024-03-01")
    if change is not None:
        print(f"✅ 贵州茅台 2024-03-01 涨跌幅: {change:+.2f}%")
    else:
        print("❌ 获取失败")
    
    # 测试获取港股数据
    print("\n测试获取腾讯控股 2024-03-01 数据:")
    change = yahoo.get_stock_history("00700", "2024-03-01")
    if change is not None:
        print(f"✅ 腾讯控股 2024-03-01 涨跌幅: {change:+.2f}%")
    else:
        print("❌ 获取失败")
    
    # 测试获取指数数据
    print("\n测试获取恒生指数 2024-03-01 数据:")
    change = yahoo.get_index_history("恒生指数", "2024-03-01")
    if change is not None:
        print(f"✅ 恒生指数 2024-03-01 涨跌幅: {change:+.2f}%")
    else:
        print("❌ 获取失败")
