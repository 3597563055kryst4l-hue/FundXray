"""
数据源管理器
自动选择可用的数据源
版本: 1.0.0

优先级：akshare > yfinance > 模拟数据
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataSourceManager:
    """
    数据源管理器
    
    自动尝试多个数据源，返回第一个成功的结果
    """
    
    def __init__(self):
        self.akshare_available = self._check_akshare()
        self.yahoo_available = self._check_yahoo()
        
        logger.info(f"数据源状态: akshare={'✅' if self.akshare_available else '❌'}, "
                   f"yfinance={'✅' if self.yahoo_available else '❌'}")
    
    def _check_akshare(self) -> bool:
        """检查 akshare 是否可用"""
        try:
            import akshare as ak
            # 尝试获取基金列表
            df = ak.fund_name_em()
            return not df.empty
        except:
            return False
    
    def _check_yahoo(self) -> bool:
        """检查 yfinance 是否可用"""
        try:
            import yfinance as yf
            ticker = yf.Ticker("AAPL")
            df = ticker.history(period="5d")
            return not df.empty
        except:
            return False
    
    def get_stock_history(self, code: str, date: str) -> Optional[float]:
        """
        获取股票历史涨跌幅，自动选择数据源
        
        参数:
            code: 股票代码
            date: 日期 'YYYY-MM-DD'
        
        返回:
            涨跌幅 %，失败返回 None
        """
        # 尝试 akshare
        if self.akshare_available:
            try:
                from data_collector import FundDataCollector
                collector = FundDataCollector()
                changes = collector.get_stock_history_changes([code], date)
                if code in changes and changes[code] != 0:
                    return changes[code]
            except Exception as e:
                logger.debug(f"akshare 获取 {code} 失败: {e}")
        
        # 尝试 yfinance
        if self.yahoo_available:
            try:
                from yahoo_data_source import YahooDataSource
                yahoo = YahooDataSource()
                change = yahoo.get_stock_history(code, date)
                if change is not None:
                    return change
            except Exception as e:
                logger.debug(f"yfinance 获取 {code} 失败: {e}")
        
        return None
    
    def get_index_history(self, index_name: str, date: str) -> Optional[float]:
        """
        获取指数历史涨跌幅，自动选择数据源
        """
        # 尝试 akshare
        if self.akshare_available:
            try:
                from data_collector import FundDataCollector
                collector = FundDataCollector()
                change = collector.get_index_history_change(index_name, date)
                if change != 0:
                    return change
            except Exception as e:
                logger.debug(f"akshare 获取指数 {index_name} 失败: {e}")
        
        # 尝试 yfinance
        if self.yahoo_available:
            try:
                from yahoo_data_source import YahooDataSource
                yahoo = YahooDataSource()
                change = yahoo.get_index_history(index_name, date)
                if change is not None:
                    return change
            except Exception as e:
                logger.debug(f"yfinance 获取指数 {index_name} 失败: {e}")
        
        return None
    
    def get_batch_stock_history(self, codes: List[str], date: str) -> Dict[str, float]:
        """
        批量获取股票历史涨跌幅
        """
        results = {}
        
        for code in codes:
            change = self.get_stock_history(code, date)
            if change is not None:
                results[code] = change
        
        return results
    
    def get_data_source_status(self) -> Dict[str, bool]:
        """获取数据源状态"""
        return {
            'akshare': self.akshare_available,
            'yfinance': self.yahoo_available,
        }


if __name__ == '__main__':
    # 测试数据源管理器
    print("测试数据源管理器...")
    
    manager = DataSourceManager()
    
    status = manager.get_data_source_status()
    print(f"\n数据源状态:")
    for name, available in status.items():
        print(f"  {'✅' if available else '❌'} {name}")
    
    # 测试获取数据
    test_date = "2024-03-01"
    
    print(f"\n测试获取贵州茅台 {test_date} 数据:")
    change = manager.get_stock_history("600519", test_date)
    if change is not None:
        print(f"✅ 涨跌幅: {change:+.2f}%")
    else:
        print("❌ 获取失败")
    
    print(f"\n测试获取恒生指数 {test_date} 数据:")
    change = manager.get_index_history("恒生指数", test_date)
    if change is not None:
        print(f"✅ 涨跌幅: {change:+.2f}%")
    else:
        print("❌ 获取失败")
