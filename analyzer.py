"""
FundXray 核心分析模块
基金经理"折腾指数"计算引擎
版本: 1.0.0

改进：考虑系统估值偏差，使用校准后的偏差进行分析
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
import json


@dataclass
class DailyDeviation:
    """单日估值偏差数据"""
    date: str
    estimated_change: float      # 日内估值涨跌幅(%)
    actual_change: float         # 实际净值涨跌幅(%)
    raw_deviation: float         # 原始偏差 = 实际 - 估值(%)
    calibrated_deviation: float  # 校准后偏差（扣除系统偏差）
    
    @property
    def abs_raw_deviation(self) -> float:
        return abs(self.raw_deviation)
    
    @property
    def abs_calibrated_deviation(self) -> float:
        return abs(self.calibrated_deviation)


@dataclass
class SystematicBias:
    """系统偏差统计"""
    mean_bias: float             # 平均偏差
    std_bias: float              # 标准差
    sample_size: int             # 样本数量
    confidence: float            # 置信度 (0-1)
    
    def is_reliable(self) -> bool:
        """判断系统偏差统计是否可靠"""
        return self.sample_size >= 10 and self.confidence > 0.5


@dataclass
class WeeklyMetrics:
    """周度折腾指标"""
    week_start: str
    week_end: str
    zheteng_index: float           # 0-10分
    end_of_month_score: float      # 0-10分
    day_trading_score: float       # 0-10分
    style_drift_score: float       # 0-10分
    summary: str
    systematic_bias: SystematicBias = field(default_factory=lambda: SystematicBias(0, 0, 0, 0))


class FundXrayAnalyzer:
    """
    基金透视仪分析器
    
    核心逻辑：
    1. 先计算历史系统估值偏差（估值方法固有的偏差）
    2. 用校准后的偏差（原始偏差 - 系统偏差）检测基金经理的"折腾"行为
    3. 这样排除了估值方法本身的影响，更能反映经理的真实操作
    """
    
    def __init__(self, fund_code: str, fund_name: str = ""):
        self.fund_code = fund_code
        self.fund_name = fund_name
        self.daily_data: List[DailyDeviation] = []
        self.systematic_bias: Optional[SystematicBias] = None
        
    def add_daily_data(self, date: str, estimated_change: float, actual_change: float):
        """添加单日数据"""
        raw_deviation = actual_change - estimated_change
        # 先添加原始数据，校准偏差在计算时处理
        self.daily_data.append(DailyDeviation(
            date=date,
            estimated_change=estimated_change,
            actual_change=actual_change,
            raw_deviation=raw_deviation,
            calibrated_deviation=raw_deviation  # 临时值，后续校准
        ))
        
    def load_data(self, data: List[Dict]):
        """批量加载数据"""
        for item in data:
            self.add_daily_data(
                date=item['date'],
                estimated_change=item['estimated_change'],
                actual_change=item['actual_change']
            )
        # 按日期排序
        self.daily_data.sort(key=lambda x: x.date)
        # 计算系统偏差并校准
        self._calculate_and_apply_systematic_bias()
        
    def _calculate_and_apply_systematic_bias(self):
        """
        计算系统估值偏差并校准数据
        
        逻辑：
        - 使用历史数据（除最近5天外）计算系统偏差
        - 系统偏差 = 平均(raw_deviation)，代表估值方法的固有偏移
        - 校准后偏差 = raw_deviation - mean_bias
        """
        if len(self.daily_data) < 10:
            # 数据不足，假设系统偏差为0
            self.systematic_bias = SystematicBias(
                mean_bias=0.0,
                std_bias=np.std([d.raw_deviation for d in self.daily_data]) if self.daily_data else 0.5,
                sample_size=len(self.daily_data),
                confidence=0.3
            )
            return
        
        # 使用历史数据（除最近window天外）计算系统偏差
        # 保留最近5天作为"当前"分析窗口
        historical_data = self.daily_data[:-5] if len(self.daily_data) > 5 else self.daily_data
        
        raw_deviations = [d.raw_deviation for d in historical_data]
        
        # 计算系统偏差统计
        mean_bias = np.mean(raw_deviations)
        std_bias = np.std(raw_deviations)
        
        # 计算置信度（基于样本数量）
        confidence = min(len(historical_data) / 20, 1.0)  # 20天达到100%置信度
        
        self.systematic_bias = SystematicBias(
            mean_bias=round(mean_bias, 3),
            std_bias=round(std_bias, 3),
            sample_size=len(historical_data),
            confidence=round(confidence, 2)
        )
        
        # 校准所有数据的偏差
        for d in self.daily_data:
            d.calibrated_deviation = d.raw_deviation - self.systematic_bias.mean_bias
            
    def calculate_weekly_score(self, window_days: int = 5) -> WeeklyMetrics:
        """
        计算周度折腾指数
        
        算法逻辑：
        1. 先计算系统估值偏差并校准
        2. 使用校准后的偏差进行分析：
           - 尾盘突击度：检测季末/月末最后几天的偏差异常
           - 做T痕迹：高频小幅波动但长期收益原地踏步
           - 风格漂移：实际与估值的系统性偏离（行业调仓）
        """
        if len(self.daily_data) < window_days:
            return WeeklyMetrics(
                week_start=self.daily_data[0].date if self.daily_data else "",
                week_end=self.daily_data[-1].date if self.daily_data else "",
                zheteng_index=0.0,
                end_of_month_score=0.0,
                day_trading_score=0.0,
                style_drift_score=0.0,
                summary="数据不足，无法分析",
                systematic_bias=self.systematic_bias or SystematicBias(0, 0, 0, 0)
            )
        
        # 确保系统偏差已计算
        if self.systematic_bias is None:
            self._calculate_and_apply_systematic_bias()
        
        # 取最近window_days数据进行分析
        recent_data = self.daily_data[-window_days:]
        
        # ========== 1. 计算尾盘突击度 ==========
        end_of_month_score = self._calculate_end_of_month_score(recent_data)
        
        # ========== 2. 计算做T痕迹 ==========
        day_trading_score = self._calculate_day_trading_score(recent_data)
        
        # ========== 3. 计算风格漂移 ==========
        style_drift_score = self._calculate_style_drift_score(recent_data)
        
        # ========== 4. 综合折腾指数 ==========
        # 权重：尾盘突击 30%，做T痕迹 40%，风格漂移 30%
        total_score = (
            end_of_month_score * 0.3 +
            day_trading_score * 0.4 +
            style_drift_score * 0.3
        )
        
        # 生成分析摘要
        summary = self._generate_summary(
            total_score, end_of_month_score, day_trading_score, style_drift_score
        )
        
        return WeeklyMetrics(
            week_start=recent_data[0].date,
            week_end=recent_data[-1].date,
            zheteng_index=round(total_score, 1),
            end_of_month_score=round(end_of_month_score, 1),
            day_trading_score=round(day_trading_score, 1),
            style_drift_score=round(style_drift_score, 1),
            summary=summary,
            systematic_bias=self.systematic_bias or SystematicBias(0, 0, 0, 0)
        )
        
    def _calculate_end_of_month_score(self, data: List[DailyDeviation]) -> float:
        """
        尾盘突击度检测
        
        逻辑：
        - 检测月末/季末最后1-2天的校准后偏差是否异常放大
        - 如果最后几天偏差突然增大，可能是临时调仓粉饰业绩
        """
        if len(data) < 3:
            return 0.0
            
        # 使用校准后的绝对偏差
        # 计算前N-2天的平均绝对偏差
        early_days = data[:-2]
        early_avg_deviation = np.mean([d.abs_calibrated_deviation for d in early_days])
        early_std_deviation = np.std([d.abs_calibrated_deviation for d in early_days]) if len(early_days) > 1 else 0.5
        
        # 最后两天的偏差
        last_two_days = data[-2:]
        last_max_deviation = max([d.abs_calibrated_deviation for d in last_two_days])
        
        # 如果最后两天偏差显著大于前期平均（超过2个标准差），则突击度高
        if early_std_deviation < 0.1:  # 避免除零
            early_std_deviation = 0.1
            
        z_score = (last_max_deviation - early_avg_deviation) / early_std_deviation
        
        # 转换为0-10分（确保不会为负数）
        if z_score <= 0:
            score = 0.0  # 没有突击迹象
        elif z_score < 1:
            score = z_score * 2  # 0-2分
        elif z_score < 2:
            score = 2 + (z_score - 1) * 3  # 2-5分
        else:
            score = 5 + min((z_score - 2) * 2.5, 5)  # 5-10分
            
        return max(0.0, min(score, 10.0))
        
    def _calculate_day_trading_score(self, data: List[DailyDeviation]) -> float:
        """
        做T痕迹检测
        
        逻辑：
        - 使用校准后的偏差
        - 日内波动频繁（偏差正负交替）
        - 但累计收益与估值收益接近（原地踏步）
        - 说明经理在做T，但效果不明显
        """
        if len(data) < 5:
            return 0.0
            
        # 使用校准后的偏差
        calibrated_deviations = [d.calibrated_deviation for d in data]
        
        # 1. 计算偏差的方向变化次数（正负交替）
        sign_changes = 0
        for i in range(1, len(calibrated_deviations)):
            if calibrated_deviations[i-1] * calibrated_deviations[i] < 0:  # 正负变化
                sign_changes += 1
                
        # 2. 计算累计偏差（应该接近0才是原地踏步）
        cumulative_deviation = abs(sum(calibrated_deviations))
        
        # 3. 计算偏差的波动性（方差）
        deviation_variance = np.var(calibrated_deviations) if len(calibrated_deviations) > 1 else 0
        
        # 评分逻辑
        # 方向变化多 + 累计偏差小 + 方差大 = 做T痕迹明显
        
        # 方向变化分数 (0-3分)
        change_ratio = sign_changes / (len(data) - 1) if len(data) > 1 else 0
        change_score = min(change_ratio * 4, 3.0)
        
        # 累计偏差分数 (0-3分) - 累计偏差越小分数越高
        avg_daily_return = np.mean([abs(d.actual_change) for d in data]) if data else 0.5
        if avg_daily_return < 0.1:
            avg_daily_return = 0.1
        cumulative_score = max(0, 3 - cumulative_deviation / (avg_daily_return * len(data)) * 3)
        
        # 方差分数 (0-4分)
        variance_threshold = 0.5  # 方差阈值
        variance_score = min(deviation_variance / variance_threshold * 4, 4.0)
        
        total_score = change_score + cumulative_score + variance_score
        return min(total_score, 10.0)
        
    def _calculate_style_drift_score(self, data: List[DailyDeviation]) -> float:
        """
        风格漂移检测
        
        逻辑：
        - 使用校准后的偏差
        - 估值与实际净值出现系统性偏离
        - 偏离方向一致且持续，说明调仓到了不同行业/风格
        """
        if len(data) < 3:
            return 0.0
            
        # 使用校准后的偏差
        calibrated_deviations = [d.calibrated_deviation for d in data]
        
        # 1. 计算系统性偏离（平均偏差）
        mean_deviation = np.mean(calibrated_deviations)
        
        # 2. 计算偏离的一致性（同号比例）
        positive_count = sum(1 for d in calibrated_deviations if d > 0)
        negative_count = len(calibrated_deviations) - positive_count
        consistency = max(positive_count, negative_count) / len(calibrated_deviations)
        
        # 3. 计算偏离的显著性（t统计量近似）
        std_deviation = np.std(calibrated_deviations) if len(calibrated_deviations) > 1 else 0.1
        if std_deviation < 0.1:
            std_deviation = 0.1
        t_stat = abs(mean_deviation) / (std_deviation / np.sqrt(len(calibrated_deviations)))
        
        # 评分逻辑
        # 一致性高 + 显著性高 = 风格漂移明显
        
        # 一致性分数 (0-4分)
        consistency_score = (consistency - 0.5) * 2 * 4  # 从0.5开始计分
        consistency_score = max(0, min(consistency_score, 4.0))
        
        # 显著性分数 (0-4分)
        significance_score = min(t_stat / 2 * 4, 4.0)
        
        # 平均绝对偏差分数 (0-2分)
        avg_abs_deviation = np.mean([abs(d) for d in calibrated_deviations])
        magnitude_score = min(avg_abs_deviation * 2, 2.0)
        
        total_score = consistency_score + significance_score + magnitude_score
        return min(total_score, 10.0)
        
    def _generate_summary(self, total: float, end_month: float, day_trade: float, style: float) -> str:
        """生成分析摘要"""
        if total < 3:
            return "老实持有型：基金经理操作谨慎，与季报披露持仓基本一致，适合长期持有。"
        elif total < 5:
            return "轻度操作型：存在轻微调仓痕迹，可能是正常的市场应对，无需过度担忧。"
        elif total < 7:
            return "中度折腾型：检测到明显的交易痕迹，建议关注后续季报是否有持仓变化。"
        else:
            reasons = []
            if end_month >= 6:
                reasons.append("尾盘突击")
            if day_trade >= 6:
                reasons.append("高频做T")
            if style >= 6:
                reasons.append("风格漂移")
            
            reason_str = "、".join(reasons) if reasons else "多项指标"
            return f"高度折腾型：检测到{reason_str}，基金经理可能在积极调仓或粉饰业绩，建议密切关注。"
            
    def get_daily_details(self) -> pd.DataFrame:
        """获取每日详细数据"""
        if not self.daily_data:
            return pd.DataFrame()
            
        data = []
        for d in self.daily_data:
            data.append({
                '日期': d.date,
                '估值涨跌幅(%)': round(d.estimated_change, 2),
                '实际涨跌幅(%)': round(d.actual_change, 2),
                '原始偏差(%)': round(d.raw_deviation, 2),
                '系统偏差(%)': round(self.systematic_bias.mean_bias if self.systematic_bias else 0, 2),
                '校准后偏差(%)': round(d.calibrated_deviation, 2),
                '绝对偏差(%)': round(d.abs_calibrated_deviation, 2)
            })
        return pd.DataFrame(data)
        
    def detect_anomalies(self, threshold: float = 2.0) -> List[Dict]:
        """
        检测异常交易日
        
        返回校准后偏差超过阈值（标准差倍数）的异常日期
        """
        if len(self.daily_data) < 3:
            return []
            
        # 使用校准后的偏差
        calibrated_deviations = [d.calibrated_deviation for d in self.daily_data]
        mean_dev = np.mean(calibrated_deviations)
        std_dev = np.std(calibrated_deviations)
        
        anomalies = []
        for d in self.daily_data:
            z_score = (d.calibrated_deviation - mean_dev) / std_dev if std_dev > 0 else 0
            if abs(z_score) > threshold:
                anomalies.append({
                    'date': d.date,
                    'raw_deviation': round(d.raw_deviation, 2),
                    'calibrated_deviation': round(d.calibrated_deviation, 2),
                    'z_score': round(z_score, 2),
                    'type': '正向异常' if d.calibrated_deviation > 0 else '负向异常'
                })
                
        return anomalies
        
    def get_systematic_bias_report(self) -> str:
        """获取系统偏差报告"""
        if not self.systematic_bias:
            return "系统偏差: 未计算"
        
        bias = self.systematic_bias
        reliability = "可靠" if bias.is_reliable() else "仅供参考"
        
        report = f"""
系统估值偏差分析:
  平均偏差: {bias.mean_bias:+.3f}%
  标准差: {bias.std_bias:.3f}%
  样本数量: {bias.sample_size}天
  置信度: {bias.confidence*100:.0f}%
  可靠性: {reliability}
  
说明: 
  系统偏差是估值方法固有的偏移，已自动扣除。
  正偏差表示估值通常低估，负偏差表示估值通常高估。
        """
        return report
