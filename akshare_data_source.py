"""
AkShare 数据源模块 - 完整版
集成所有可用的akshare接口
版本: 1.0.0
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AkShareDataSource:
    """
    AkShare 数据源 - 使用新浪财经接口（东方财富被限制）
    
    支持：
    - A股：stock_zh_a_daily
    - A股指数：stock_zh_index_daily
    - 港股：stock_hk_daily
    - 港股指数：stock_hk_index_daily_sina
    - 美股：stock_us_daily
    
    优化：
    - 使用缓存避免重复获取相同股票数据
    - 批量处理减少API调用次数
    """
    
    def __init__(self):
        # 指数代码映射
        # A股指数使用新浪财经格式 (sh/sz + 代码)
        # 港股指数使用HSI等简写
        # 美股指数使用ETF代码 (如QQQ代表纳斯达克100)
        self.index_mapping = {
            '上证指数': 'sh000001',
            '深证成指': 'sz399001',
            '创业板指': 'sz399006',
            '沪深300': 'sh000300',
            '中证500': 'sh000905',
            '恒生指数': 'HSI',
            '纳斯达克100': 'QQQ',  # 使用QQQ ETF代表纳斯达克100
        }
        
        # 数据缓存：{股票代码: DataFrame}
        self._cache = {}
        
    def _get_cached_data(self, cache_key: str, fetch_func) -> pd.DataFrame:
        """
        获取缓存数据，如果不存在则调用fetch_func获取
        
        参数:
            cache_key: 缓存键
            fetch_func: 获取数据的函数
        
        返回:
            DataFrame
        """
        if cache_key not in self._cache:
            logger.debug(f"缓存未命中: {cache_key}，正在获取数据...")
            df = fetch_func()
            if not df.empty:
                self._cache[cache_key] = df
        else:
            logger.debug(f"缓存命中: {cache_key}")
        
        return self._cache.get(cache_key, pd.DataFrame())
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        logger.info("数据缓存已清除")
    
    def _convert_a_stock_code(self, code: str) -> str:
        """转换A股代码为新浪财经格式"""
        code = str(code).strip()
        if len(code) == 6 and code.isdigit():
            if code.startswith('6'):
                return f"sh{code}"
            else:
                return f"sz{code}"
        return code
    
    def _convert_hk_stock_code(self, code: str) -> str:
        """转换港股代码"""
        code = str(code).strip()
        # 去掉hk前缀如果有
        if code.lower().startswith('hk'):
            code = code[2:]
        return code
    
    def get_a_stock_history(self, code: str, date: str) -> float:
        """
        获取A股历史涨跌幅
        使用: stock_zh_a_daily (新浪财经)
        优化: 使用缓存避免重复获取
        """
        try:
            sina_code = self._convert_a_stock_code(code)
            cache_key = f"a_stock_{sina_code}"
            
            # 使用缓存获取数据
            def fetch_data():
                return ak.stock_zh_a_daily(symbol=sina_code, adjust="qfq")
            
            df = self._get_cached_data(cache_key, fetch_data)
            
            if df.empty:
                raise ValueError(f"无法获取A股 {code} 的历史数据")
            
            # 设置日期索引（如果还没有设置）
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            
            # 查找目标日期
            target_data = df[df.index.strftime('%Y-%m-%d') == date]
            if target_data.empty:
                available = df.index.strftime('%Y-%m-%d').tolist()[-5:]
                raise ValueError(f"A股 {code} 无 {date} 数据，最近: {available}")
            
            # 计算涨跌幅
            idx = df.index.get_loc(target_data.index[0])
            if idx <= 0:
                raise ValueError(f"A股 {code} 在 {date} 无前一日数据")
            
            curr = float(target_data.iloc[0]['close'])
            prev = float(df.iloc[idx-1]['close'])
            change = (curr - prev) / prev * 100
            
            return round(change, 2)
            
        except Exception as e:
            logger.error(f"AkShare A股 {code} {date} 失败: {e}")
            raise ValueError(f"无法获取A股 {code} 在 {date} 的数据: {e}")
    
    def get_hk_stock_history(self, code: str, date: str) -> float:
        """
        获取港股历史涨跌幅
        使用: stock_hk_daily (新浪财经)
        优化: 使用缓存避免重复获取
        """
        try:
            hk_code = self._convert_hk_stock_code(code)
            cache_key = f"hk_stock_{hk_code}"
            
            # 使用缓存获取数据
            def fetch_data():
                return ak.stock_hk_daily(symbol=hk_code, adjust="qfq")
            
            df = self._get_cached_data(cache_key, fetch_data)
            
            if df.empty:
                raise ValueError(f"无法获取港股 {code} 的历史数据")
            
            # 设置日期索引（如果还没有设置）
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            
            # 查找目标日期
            target_data = df[df.index.strftime('%Y-%m-%d') == date]
            if target_data.empty:
                available = df.index.strftime('%Y-%m-%d').tolist()[-5:]
                raise ValueError(f"港股 {code} 无 {date} 数据，最近: {available}")
            
            # 计算涨跌幅
            idx = df.index.get_loc(target_data.index[0])
            if idx <= 0:
                raise ValueError(f"港股 {code} 在 {date} 无前一日数据")
            
            curr = float(target_data.iloc[0]['close'])
            prev = float(df.iloc[idx-1]['close'])
            change = (curr - prev) / prev * 100
            
            return round(change, 2)
            
        except Exception as e:
            logger.error(f"AkShare港股 {code} {date} 失败: {e}")
            raise ValueError(f"无法获取港股 {code} 在 {date} 的数据: {e}")
    
    def get_us_stock_history(self, code: str, date: str) -> float:
        """
        获取美股历史涨跌幅
        使用: stock_us_daily (新浪财经)
        优化: 使用缓存避免重复获取
        """
        try:
            cache_key = f"us_stock_{code}"
            
            # 使用缓存获取数据
            def fetch_data():
                return ak.stock_us_daily(symbol=code, adjust="qfq")
            
            df = self._get_cached_data(cache_key, fetch_data)
            
            if df.empty:
                raise ValueError(f"无法获取美股 {code} 的历史数据")
            
            # 设置日期索引（如果还没有设置）
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            
            # 查找目标日期
            target_data = df[df.index.strftime('%Y-%m-%d') == date]
            if target_data.empty:
                available = df.index.strftime('%Y-%m-%d').tolist()[-5:]
                raise ValueError(f"美股 {code} 无 {date} 数据，最近: {available}")
            
            # 计算涨跌幅
            idx = df.index.get_loc(target_data.index[0])
            if idx <= 0:
                raise ValueError(f"美股 {code} 在 {date} 无前一日数据")
            
            curr = float(target_data.iloc[0]['close'])
            prev = float(df.iloc[idx-1]['close'])
            change = (curr - prev) / prev * 100
            
            return round(change, 2)
            
        except Exception as e:
            logger.error(f"AkShare美股 {code} {date} 失败: {e}")
            raise ValueError(f"无法获取美股 {code} 在 {date} 的数据: {e}")
    
    def get_index_history(self, index_name: str, date: str) -> float:
        """
        获取指数历史涨跌幅
        优化: 使用缓存避免重复获取
        """
        if index_name not in self.index_mapping:
            raise ValueError(f"未知指数: {index_name}")
        
        code = self.index_mapping[index_name]
        cache_key = f"index_{code}"
        
        try:
            # A股指数
            if code.startswith(('sh', 'sz')):
                def fetch_a_index():
                    return ak.stock_zh_index_daily(symbol=code)
                
                df = self._get_cached_data(cache_key, fetch_a_index)
                
                if df.empty:
                    raise ValueError(f"无法获取指数 {index_name} 的数据")
                
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                
                target_data = df[df.index.strftime('%Y-%m-%d') == date]
                if target_data.empty:
                    available = df.index.strftime('%Y-%m-%d').tolist()[-5:]
                    raise ValueError(f"指数 {index_name} 无 {date} 数据，最近: {available}")
                
                idx = df.index.get_loc(target_data.index[0])
                if idx <= 0:
                    raise ValueError(f"指数 {index_name} 在 {date} 无前一日数据")
                
                curr = float(target_data.iloc[0]['close'])
                prev = float(df.iloc[idx-1]['close'])
                change = (curr - prev) / prev * 100
                
                return round(change, 2)
            
            # 港股指数
            elif code == 'HSI':
                def fetch_hk_index():
                    return ak.stock_hk_index_daily_sina(symbol=code)
                
                df = self._get_cached_data(cache_key, fetch_hk_index)
                
                if df.empty:
                    raise ValueError(f"无法获取指数 {index_name} 的数据")
                
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                
                target_data = df[df.index.strftime('%Y-%m-%d') == date]
                if target_data.empty:
                    available = df.index.strftime('%Y-%m-%d').tolist()[-5:]
                    raise ValueError(f"指数 {index_name} 无 {date} 数据，最近: {available}")
                
                idx = df.index.get_loc(target_data.index[0])
                if idx <= 0:
                    raise ValueError(f"指数 {index_name} 在 {date} 无前一日数据")
                
                curr = float(target_data.iloc[0]['close'])
                prev = float(df.iloc[idx-1]['close'])
                change = (curr - prev) / prev * 100
                
                return round(change, 2)
            
            # 美股指数（使用ETF代码，如QQQ）
            elif code.isalpha():
                # 使用美股接口获取ETF数据（使用缓存）
                def fetch_us_index():
                    return ak.stock_us_daily(symbol=code, adjust="qfq")
                
                df = self._get_cached_data(cache_key, fetch_us_index)
                
                if df.empty:
                    raise ValueError(f"无法获取指数 {index_name} 的数据")
                
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                
                target_data = df[df.index.strftime('%Y-%m-%d') == date]
                if target_data.empty:
                    available = df.index.strftime('%Y-%m-%d').tolist()[-5:]
                    raise ValueError(f"指数 {index_name} 无 {date} 数据，最近: {available}")
                
                idx = df.index.get_loc(target_data.index[0])
                if idx <= 0:
                    raise ValueError(f"指数 {index_name} 在 {date} 无前一日数据")
                
                curr = float(target_data.iloc[0]['close'])
                prev = float(df.iloc[idx-1]['close'])
                change = (curr - prev) / prev * 100
                
                return round(change, 2)
            
            else:
                raise ValueError(f"不支持的指数: {index_name}")
                
        except Exception as e:
            logger.error(f"AkShare指数 {index_name} {date} 失败: {e}")
            raise ValueError(f"无法获取指数 {index_name} 在 {date} 的数据: {e}")
    
    def get_stock_history(self, code: str, date: str) -> float:
        """
        智能获取股票历史涨跌幅（自动判断市场）
        """
        code = str(code).strip()
        
        # A股
        if len(code) == 6 and code.isdigit():
            return self.get_a_stock_history(code, date)
        
        # 港股
        elif len(code) == 5 and code.isdigit():
            return self.get_hk_stock_history(code, date)
        
        # 美股（字母代码）
        elif code.isalpha():
            return self.get_us_stock_history(code, date)
        
        else:
            raise ValueError(f"无法识别股票代码格式: {code}")
    
    def get_batch_stock_changes(self, codes: List[str], date: str) -> Dict[str, float]:
        """批量获取股票涨跌幅"""
        results = {}
        
        for code in codes:
            try:
                change = self.get_stock_history(code, date)
                results[code] = change
            except Exception as e:
                logger.error(f"批量获取 {code} 失败: {e}")
                raise
        
        return results


if __name__ == '__main__':
    # 测试
    print("测试 AkShare 完整数据源...")
    
    ds = AkShareDataSource()
    test_date = "2024-03-01"
    
    # 测试A股
    print(f"\n1. A股 600519 {test_date}:")
    try:
        change = ds.get_a_stock_history("600519", test_date)
        print(f"   ✅ 涨跌幅: {change:+.2f}%")
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试港股
    print(f"\n2. 港股 00700 {test_date}:")
    try:
        change = ds.get_hk_stock_history("00700", test_date)
        print(f"   ✅ 涨跌幅: {change:+.2f}%")
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试美股
    print(f"\n3. 美股 AAPL {test_date}:")
    try:
        change = ds.get_us_stock_history("AAPL", test_date)
        print(f"   ✅ 涨跌幅: {change:+.2f}%")
    except Exception as e:
        print(f"   ❌ {e}")
    
    # 测试指数
    print(f"\n4. 上证指数 {test_date}:")
    try:
        change = ds.get_index_history("上证指数", test_date)
        print(f"   ✅ 涨跌幅: {change:+.2f}%")
    except Exception as e:
        print(f"   ❌ {e}")
    
    print(f"\n5. 恒生指数 {test_date}:")
    try:
        change = ds.get_index_history("恒生指数", test_date)
        print(f"   ✅ 涨跌幅: {change:+.2f}%")
    except Exception as e:
        print(f"   ❌ {e}")
    
    print("\n测试完成")
