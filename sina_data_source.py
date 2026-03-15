"""
新浪财经数据源模块
使用akshare中可用的新浪财经接口
版本: 1.0.0
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SinaDataSource:
    """
    新浪财经数据源
    
    使用akshare中可用的新浪财经接口：
    - stock_zh_a_daily: A股历史数据
    - stock_zh_index_daily: A股指数历史数据
    - stock_hk_index_daily_sina: 港股指数历史数据
    """
    
    def __init__(self):
        self.index_mapping = {
            '上证指数': 'sh000001',
            '深证成指': 'sz399001',
            '创业板指': 'sz399006',
            '沪深300': 'sh000300',
            '中证500': 'sh000905',
            '恒生指数': 'HSI',
        }
    
    def _convert_stock_code(self, code: str) -> str:
        """转换为新浪财经格式"""
        code = str(code).strip()
        
        # A股
        if len(code) == 6 and code.isdigit():
            if code.startswith('6'):
                return f"sh{code}"
            else:
                return f"sz{code}"
        
        return code
    
    def get_stock_history(self, code: str, date: str) -> float:
        """
        获取股票在某一天的历史涨跌幅
        
        参数:
            code: 股票代码
            date: 日期 'YYYY-MM-DD'
        
        返回:
            涨跌幅 %
        
        异常:
            ValueError: 当无法获取数据时抛出
        """
        try:
            sina_code = self._convert_stock_code(code)
            
            # 使用新浪财经接口获取A股历史数据
            df = ak.stock_zh_a_daily(symbol=sina_code, adjust="qfq")
            
            if df.empty:
                raise ValueError(f"无法获取 {code} 的历史数据")
            
            # 将date列转换为datetime并设为索引
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
            
            # 找到目标日期
            target_data = df[df.index.strftime('%Y-%m-%d') == date]
            
            if target_data.empty:
                available_dates = df.index.strftime('%Y-%m-%d').tolist()[-10:]
                raise ValueError(f"无法获取 {code} 在 {date} 的数据，最近可用日期: {available_dates}")
            
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
            
        except Exception as e:
            logger.error(f"新浪财经: 获取 {code} {date} 数据失败: {e}")
            raise ValueError(f"无法获取股票 {code} 在 {date} 的数据: {e}")
    
    def get_index_change(self, index_name: str, date: str) -> float:
        """
        获取指数在某一天的涨跌幅
        """
        if index_name not in self.index_mapping:
            raise ValueError(f"未知指数: {index_name}")
        
        code = self.index_mapping[index_name]
        
        try:
            # A股指数
            if code.startswith(('sh', 'sz')):
                df = ak.stock_zh_index_daily(symbol=code)
                
                if df.empty:
                    raise ValueError(f"无法获取指数 {index_name} 的历史数据")
                
                # 将date列转换为datetime并设为索引
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
                
                # 找到目标日期
                target_data = df[df.index.strftime('%Y-%m-%d') == date]
                
                if target_data.empty:
                    available_dates = df.index.strftime('%Y-%m-%d').tolist()[-10:]
                    raise ValueError(f"无法获取 {index_name} 在 {date} 的数据，最近可用日期: {available_dates}")
                
                # 计算涨跌幅
                idx = target_data.index[0]
                idx_loc = df.index.get_loc(idx)
                
                if idx_loc <= 0:
                    raise ValueError(f"无法计算 {index_name} 在 {date} 的涨跌幅")
                
                curr_close = float(target_data.iloc[0]['close'])
                prev_close = float(df.iloc[idx_loc - 1]['close'])
                
                if prev_close <= 0:
                    raise ValueError(f"{index_name} 在 {date} 的前一日收盘价异常")
                
                change_pct = (curr_close - prev_close) / prev_close * 100
                return round(change_pct, 2)
            
            # 港股指数
            elif code == 'HSI':
                df = ak.stock_hk_index_daily_sina(symbol=code)
                
                if df.empty:
                    raise ValueError(f"无法获取指数 {index_name} 的历史数据")
                
                df['date'] = pd.to_datetime(df['date'])
                target_data = df[df['date'].dt.strftime('%Y-%m-%d') == date]
                
                if target_data.empty:
                    available_dates = df['date'].dt.strftime('%Y-%m-%d').tolist()[-10:]
                    raise ValueError(f"无法获取 {index_name} 在 {date} 的数据，最近可用日期: {available_dates}")
                
                # 计算涨跌幅
                idx = target_data.index[0]
                idx_loc = df.index.get_loc(idx)
                
                if idx_loc <= 0:
                    raise ValueError(f"无法计算 {index_name} 在 {date} 的涨跌幅")
                
                curr_close = float(target_data.iloc[0]['close'])
                prev_close = float(df.iloc[idx_loc - 1]['close'])
                
                if prev_close <= 0:
                    raise ValueError(f"{index_name} 在 {date} 的前一日收盘价异常")
                
                change_pct = (curr_close - prev_close) / prev_close * 100
                return round(change_pct, 2)
            
            else:
                raise ValueError(f"不支持的指数代码: {code}")
                
        except Exception as e:
            logger.error(f"新浪财经: 获取指数 {index_name} {date} 数据失败: {e}")
            raise ValueError(f"无法获取指数 {index_name} 在 {date} 的数据: {e}")
    
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
    # 测试新浪财经数据源
    print("测试新浪财经数据源...")
    
    sina = SinaDataSource()
    
    # 测试A股
    print("\n1. 测试A股 600519 2024-03-01:")
    try:
        change = sina.get_stock_history("600519", "2024-03-01")
        print(f"   ✅ 涨跌幅: {change:+.2f}%")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 测试A股指数
    print("\n2. 测试上证指数 2024-03-01:")
    try:
        change = sina.get_index_change("上证指数", "2024-03-01")
        print(f"   ✅ 涨跌幅: {change:+.2f}%")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    # 测试港股指数
    print("\n3. 测试恒生指数 2024-03-01:")
    try:
        change = sina.get_index_change("恒生指数", "2024-03-01")
        print(f"   ✅ 涨跌幅: {change:+.2f}%")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print("\n测试完成")
