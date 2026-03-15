"""
FundXray 可视化报告模块
生成命令行报告和简单图表
版本: 1.0.0
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.dates import DateFormatter
import pandas as pd
from datetime import datetime
from typing import List, Dict
import os

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class FundXrayVisualizer:
    """
    基金透视仪可视化器
    
    生成：
    1. 命令行文本报告
    2. 简单可视化图表
    """
    
    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def print_console_report(self, fund_code: str, fund_name: str, 
                            metrics, daily_df: pd.DataFrame, anomalies: List[Dict]):
        """
        打印命令行报告
        """
        # ANSI颜色代码
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        BOLD = '\033[1m'
        END = '\033[0m'
        
        # 根据分数选择颜色
        def score_color(score):
            if score < 3:
                return GREEN
            elif score < 5:
                return YELLOW
            elif score < 7:
                return '\033[38;5;208m'  # Orange
            else:
                return RED
        
        # 打印标题
        print("\n" + "=" * 70)
        print(f"{BOLD}{CYAN}🔍 FundXray 基金透视仪 - 基金经理折腾指数报告{END}")
        print("=" * 70)
        
        # 基金信息
        print(f"\n{BOLD}📊 基金信息{END}")
        print(f"   基金代码: {fund_code}")
        print(f"   基金名称: {fund_name}")
        print(f"   分析周期: {metrics.week_start} 至 {metrics.week_end}")
        
        # 系统偏差信息
        bias = metrics.systematic_bias
        if bias and bias.sample_size > 0:
            print(f"\n{BOLD}⚙️ 系统估值偏差校准{END}")
            print(f"   历史平均偏差: {bias.mean_bias:+.3f}%")
            print(f"   标准差: {bias.std_bias:.3f}%")
            print(f"   校准样本: {bias.sample_size}天")
            reliability = f"{GREEN}可靠{END}" if bias.is_reliable() else f"{YELLOW}仅供参考{END}"
            print(f"   可靠性: {reliability}")
            print(f"   {CYAN}说明: 已自动扣除系统偏差，更准确检测经理操作{END}")
        
        # 核心指标
        print(f"\n{BOLD}📈 核心指标{END}")
        
        total_color = score_color(metrics.zheteng_index)
        print(f"\n   {BOLD}{total_color}▶ 折腾指数: {metrics.zheteng_index}/10{END}")
        
        # 进度条
        bar_length = 30
        filled = int(metrics.zheteng_index / 10 * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"   [{total_color}{bar}{END}]")
        
        # 评级
        if metrics.zheteng_index < 3:
            level = f"{GREEN}老实持有型 ⭐⭐⭐{END}"
        elif metrics.zheteng_index < 5:
            level = f"{YELLOW}轻度操作型 ⭐⭐{END}"
        elif metrics.zheteng_index < 7:
            level = f"\033[38;5;208m中度折腾型 ⭐{END}"
        else:
            level = f"{RED}高度折腾型 ⚠️{END}"
        print(f"   评级: {level}")
        
        # 分项指标
        print(f"\n{BOLD}📋 分项指标{END}")
        
        end_color = score_color(metrics.end_of_month_score)
        print(f"   • 尾盘突击度: {end_color}{metrics.end_of_month_score}/10{END}", end="")
        if metrics.end_of_month_score >= 6:
            print(f" {RED}[⚠️ 检测到尾盘突击行为]{END}")
        else:
            print()
            
        trade_color = score_color(metrics.day_trading_score)
        print(f"   • 做T痕迹分: {trade_color}{metrics.day_trading_score}/10{END}", end="")
        if metrics.day_trading_score >= 6:
            print(f" {YELLOW}[📊 高频交易迹象]{END}")
        else:
            print()
            
        drift_color = score_color(metrics.style_drift_score)
        print(f"   • 风格漂移分: {drift_color}{metrics.style_drift_score}/10{END}", end="")
        if metrics.style_drift_score >= 6:
            print(f" {BLUE}[🔄 可能存在调仓]{END}")
        else:
            print()
        
        # 分析摘要
        print(f"\n{BOLD}💡 分析结论{END}")
        print(f"   {metrics.summary}")
        
        # 异常交易日
        if anomalies:
            print(f"\n{BOLD}⚠️ 异常交易日检测{END}")
            print(f"   发现 {len(anomalies)} 个异常交易日:")
            for anomaly in anomalies[:5]:  # 只显示前5个
                date = anomaly['date']
                cal_dev = anomaly.get('calibrated_deviation', anomaly.get('deviation', 0))
                z_score = anomaly['z_score']
                type_str = anomaly['type']
                
                if cal_dev > 0:
                    color = RED
                    icon = "📈"
                else:
                    color = GREEN
                    icon = "📉"
                    
                print(f"   {icon} {date}: 校准偏差 {color}{cal_dev:+.2f}%{END} (Z值: {z_score:.2f}) [{type_str}]")
        
        # 每日数据表格
        print(f"\n{BOLD}📅 每日详细数据 (最近10天){END}")
        print("-" * 85)
        print(f"{'日期':<12} {'估值':<10} {'实际':<10} {'原始偏差':<10} {'校准偏差':<10} {'偏离度'}")
        print("-" * 85)
        
        recent_data = daily_df.tail(10)
        for _, row in recent_data.iterrows():
            date = row['日期']
            est = row['估值涨跌幅(%)']
            actual = row['实际涨跌幅(%)']
            raw_dev = row.get('原始偏差(%)', row.get('偏差(%)', 0))
            cal_dev = row.get('校准后偏差(%)', row.get('偏差(%)', 0))
            abs_dev = row['绝对偏差(%)']
            
            # 根据校准后偏差大小着色
            if abs_dev > 0.8:
                dev_color = RED
            elif abs_dev > 0.4:
                dev_color = YELLOW
            else:
                dev_color = GREEN
                
            print(f"{date:<12} {est:>+8.2f}% {actual:>+8.2f}% {raw_dev:>+8.2f}% {dev_color}{cal_dev:>+8.2f}%{END} {abs_dev:>7.2f}%")
        
        print("-" * 85)
        
        # 统计摘要
        avg_deviation = daily_df['绝对偏差(%)'].mean()
        max_deviation = daily_df['绝对偏差(%)'].max()
        
        print(f"\n{BOLD}📊 统计摘要{END}")
        print(f"   平均绝对偏差: {avg_deviation:.2f}%")
        print(f"   最大绝对偏差: {max_deviation:.2f}%")
        
        # 建议
        print(f"\n{BOLD}💼 投资建议{END}")
        if metrics.zheteng_index < 3:
            print(f"   {GREEN}✓{END} 基金经理操作透明，与披露持仓一致")
            print(f"   {GREEN}✓{END} 适合长期持有，无需过度关注短期波动")
        elif metrics.zheteng_index < 5:
            print(f"   {YELLOW}!{END} 存在轻微操作痕迹，建议定期关注")
            print(f"   {YELLOW}!{END} 可关注后续季报是否有持仓调整")
        elif metrics.zheteng_index < 7:
            print(f"   {RED}⚠{END} 检测到明显的交易活动")
            print(f"   {RED}⚠{END} 建议密切关注净值波动和季报披露")
        else:
            print(f"   {RED}🚨{END} 基金经理操作频繁，可能存在风格漂移")
            print(f"   {RED}🚨{END} 建议重新评估该基金是否符合投资目标")
        
        print("\n" + "=" * 70)
        print(f"{CYAN}报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{END}")
        print(f"{CYAN}免责声明: 本报告仅供参考，不构成投资建议{END}")
        print("=" * 70 + "\n")
        
    def generate_chart(self, fund_code: str, fund_name: str, 
                      daily_df: pd.DataFrame, metrics, output_file: str = None):
        """
        生成可视化图表
        """
        if output_file is None:
            output_file = os.path.join(self.output_dir, f"{fund_code}_xray.png")
        
        # 转换日期
        daily_df = daily_df.copy()
        daily_df['日期'] = pd.to_datetime(daily_df['日期'])
        
        # 创建图表
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        fig.suptitle(f'FundXray - {fund_name} ({fund_code})\n折腾指数: {metrics.折腾指数}/10', 
                     fontsize=14, fontweight='bold')
        
        # 颜色方案
        colors = {
            'primary': '#2E86AB',
            'secondary': '#A23B72',
            'accent': '#F18F01',
            'danger': '#C73E1D',
            'success': '#3B1F2B'
        }
        
        # ========== 图1: 估值 vs 实际对比 ==========
        ax1 = axes[0]
        ax1.plot(daily_df['日期'], daily_df['估值涨跌幅(%)'], 
                label='日内估值', color=colors['primary'], linewidth=2, marker='o', markersize=4)
        ax1.plot(daily_df['日期'], daily_df['实际涨跌幅(%)'], 
                label='实际净值', color=colors['secondary'], linewidth=2, marker='s', markersize=4)
        ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax1.set_title('估值与实际涨跌幅对比', fontweight='bold')
        ax1.set_ylabel('涨跌幅 (%)')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(DateFormatter('%m-%d'))
        
        # ========== 图2: 偏差分析 ==========
        ax2 = axes[1]
        deviations = daily_df['偏差(%)']
        colors_bar = [colors['danger'] if d > 0 else colors['success'] for d in deviations]
        ax2.bar(daily_df['日期'], deviations, color=colors_bar, alpha=0.7)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax2.axhline(y=deviations.mean(), color=colors['accent'], linestyle='--', 
                   label=f'平均偏差: {deviations.mean():.2f}%')
        ax2.set_title('估值偏差分析 (正=实际>估值，可能调仓)', fontweight='bold')
        ax2.set_ylabel('偏差 (%)')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.xaxis.set_major_formatter(DateFormatter('%m-%d'))
        
        # ========== 图3: 折腾指数仪表盘 ==========
        ax3 = axes[2]
        
        # 绘制仪表盘背景
        theta = [i/100 * 180 for i in range(101)]
        r = [1] * 101
        
        # 分段颜色
        for i in range(100):
            if i < 30:
                color = '#28a745'  # 绿色
            elif i < 50:
                color = '#ffc107'  # 黄色
            elif i < 70:
                color = '#fd7e14'  # 橙色
            else:
                color = '#dc3545'  # 红色
            ax3.plot([i/100 * 3.14159, (i+1)/100 * 3.14159], [1, 1], 
                    color=color, linewidth=15)
        
        # 指针
        score = metrics.zheteng_index
        angle = score / 10 * 3.14159
        ax3.annotate('', xy=(angle, 0.9), xytext=(3.14159/2, 0.3),
                    arrowprops=dict(arrowstyle='->', color='black', lw=3))
        
        # 中心文字
        ax3.text(3.14159/2, 0.3, f'{score}', fontsize=36, ha='center', va='center',
                fontweight='bold', color=self._score_color(score))
        ax3.text(3.14159/2, 0.1, '折腾指数', fontsize=12, ha='center', va='center')
        
        # 添加分项指标
        ax3.text(0.1, 0.5, f'尾盘突击度: {metrics.end_of_month_score}', fontsize=10)
        ax3.text(0.1, 0.4, f'做T痕迹分: {metrics.day_trading_score}', fontsize=10)
        ax3.text(0.1, 0.3, f'风格漂移分: {metrics.style_drift_score}', fontsize=10)
        
        ax3.set_xlim(0, 3.14159)
        ax3.set_ylim(0, 1.2)
        ax3.set_aspect('equal')
        ax3.axis('off')
        ax3.set_title('折腾指数仪表盘', fontweight='bold', y=0.95)
        
        plt.tight_layout()
        plt.savefig(output_file, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        print(f"📊 图表已保存: {output_file}")
        return output_file
        
    def _score_color(self, score: float) -> str:
        """根据分数返回颜色"""
        if score < 3:
            return '#28a745'
        elif score < 5:
            return '#ffc107'
        elif score < 7:
            return '#fd7e14'
        else:
            return '#dc3545'
            
    def generate_simple_ascii_chart(self, daily_df: pd.DataFrame, width: int = 60) -> str:
        """
        生成简单的ASCII图表（用于命令行显示）
        """
        if daily_df.empty:
            return "无数据"
        
        lines = []
        lines.append("\n偏差趋势图 (ASCII):")
        lines.append("-" * width)
        
        deviations = daily_df['偏差(%)'].tolist()
        max_dev = max(abs(min(deviations)), abs(max(deviations)), 0.1)
        
        # 绘制坐标轴
        lines.append(f" +{max_dev:5.2f}% |" + " " * (width - 12))
        lines.append(f"  0.00% |" + "-" * (width - 12))
        lines.append(f" -{max_dev:5.2f}% |" + " " * (width - 12))
        
        # 绘制数据点
        chart_width = width - 12
        step = max(1, len(deviations) // chart_width)
        
        points = []
        for i in range(0, len(deviations), step):
            dev = deviations[i]
            # 将偏差映射到0-10的范围
            normalized = int((dev + max_dev) / (2 * max_dev) * 10)
            normalized = max(0, min(10, normalized))
            points.append(normalized)
        
        # 构建图表行
        for level in range(10, -1, -1):
            row = " " * 9 + "|"
            for p in points:
                if p == level:
                    row += "*"
                elif level == 5:  # 零线
                    row += "-"
                else:
                    row += " "
            lines.append(row)
        
        lines.append("-" * width)
        lines.append(f"日期: {daily_df.iloc[0]['日期']} ... {daily_df.iloc[-1]['日期']}")
        
        return "\n".join(lines)
