#!/usr/bin/env python3
"""
FundXray - 基金透视仪
命令行入口脚本
版本: 1.0.0

使用示例:
    python fundxray.py 110011              # 分析指定基金
    python fundxray.py 110011 --days 30    # 分析30天数据
    python fundxray.py 110011 --demo       # 使用演示数据
    python fundxray.py 110011 --no-chart   # 不生成图表
    python fundxray.py 110011 --show-calc  # 显示估值计算过程
"""

import argparse
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analyzer import FundXrayAnalyzer
from data_collector import FundDataCollector, generate_demo_data
from visualizer import FundXrayVisualizer


def print_estimation_details(collector: FundDataCollector, fund_code: str, fund_name: str):
    """打印估值计算详情"""
    print(f"\n{'='*70}")
    print(f"📊 估值计算详情 - {fund_name} ({fund_code})")
    print(f"{'='*70}")
    
    # 获取持仓数据
    print("\n[1] 获取基金持仓...")
    holdings_df = collector.get_fund_holdings(fund_code)
    if holdings_df.empty:
        print("   ❌ 无法获取持仓数据")
        return
    
    print(f"   ✅ 获取到 {len(holdings_df)} 只持仓股票")
    
    # 获取详细估值计算
    print("\n[2] 计算估值...")
    result = collector.estimate_daily_change_with_details(fund_code, holdings_df)
    
    if not result:
        print("   ❌ 估值计算失败")
        return
    
    # 显示市场检测
    print(f"\n[3] 市场检测:")
    print(f"   市场类型: {result['market']}")
    print(f"   基准指数: {result['benchmark']}")
    print(f"   基准涨跌幅: {result['benchmark_change']:+.2f}%")
    
    # 显示持仓明细
    print(f"\n[4] 前十持仓明细及贡献:")
    print(f"   {'股票代码':<10} {'股票名称':<12} {'占比':<8} {'涨跌幅':<10} {'贡献度':<10}")
    print(f"   {'-'*60}")
    
    for h in result['holdings_detail'][:10]:
        print(f"   {h['code']:<10} {h['name']:<12} {h['ratio']:>6.2f}% {h['change']:>+8.2f}% {h['contrib']:>+8.3f}%")
    
    print(f"   {'-'*60}")
    print(f"   {'合计':<10} {'':<12} {result['top10_ratio']:>6.2f}% {'':<10} {result['top10_contrib']:>+8.3f}%")
    
    # 显示仓位计算
    print(f"\n[5] 仓位计算:")
    print(f"   前十持仓占比: {result['top10_ratio']:.2f}%")
    print(f"   估算股票仓位: {result['est_position']:.0f}%")
    print(f"   剩余仓位: {result['remaining_ratio']:.2f}%")
    print(f"   剩余部分贡献: {result['benchmark_change']:+.2f}% × {result['remaining_ratio']:.2f}% = {result['remaining_contrib']:+.3f}%")
    
    # 显示计算过程
    print(f"\n[6] 估值计算过程:")
    print(f"   前十持仓贡献: {result['top10_contrib']:+.3f}%")
    print(f"   剩余仓位贡献: {result['remaining_contrib']:+.3f}%")
    print(f"   小计: {result['subtotal']:+.3f}%")
    
    if result['adjustment_factor'] != 1.0:
        print(f"   市场调整系数: ×{result['adjustment_factor']}")
        print(f"   调整后: {result['subtotal']:+.3f}% × {result['adjustment_factor']} = {result['estimated_change']:+.2f}%")
    else:
        print(f"   最终估值: {result['estimated_change']:+.2f}%")
    
    print(f"\n{'='*70}")
    print(f"✅ 当日估值结果: {result['estimated_change']:+.2f}%")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='FundXray - 基金透视仪：检测基金经理的"折腾"行为',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python fundxray.py 110011                    # 分析易方达中小盘
  python fundxray.py 110011 --days 30          # 分析30天数据
  python fundxray.py 110011 --demo             # 使用演示数据
  python fundxray.py 110011 --no-chart         # 只输出文本报告
  python fundxray.py 110011 --show-calc        # 显示估值计算过程
        """
    )
    
    parser.add_argument('fund_code', type=str, help='基金代码 (6位数字)')
    parser.add_argument('--days', type=int, default=20, 
                       help='分析天数 (默认: 20)')
    parser.add_argument('--demo', action='store_true',
                       help='使用演示数据（不获取真实数据）')
    parser.add_argument('--no-chart', action='store_true',
                       help='不生成可视化图表')
    parser.add_argument('--output-dir', type=str, default='./output',
                       help='输出目录 (默认: ./output)')
    parser.add_argument('--show-calc', action='store_true',
                       help='显示当日估值计算详情')
    parser.add_argument('--show-daily-calc', action='store_true',
                       help='逐日显示估值计算过程（分析时）')
    
    args = parser.parse_args()
    
    # 验证基金代码
    if not args.fund_code.isdigit() or len(args.fund_code) != 6:
        print(f"❌ 错误: 基金代码必须是6位数字，当前: {args.fund_code}")
        sys.exit(1)
    
    print(f"\n🔍 FundXray 基金透视仪启动...")
    print(f"   目标基金: {args.fund_code}")
    print(f"   分析周期: 最近 {args.days} 天")
    
    # 如果要求显示计算详情
    if args.show_calc:
        if args.demo:
            # 演示模式下显示示例计算过程
            print("\n📊 演示模式 - 估值计算过程示例")
            print("="*70)
            print("\n[1] 获取基金持仓...")
            print("   ✅ 获取到 10 只持仓股票")
            
            print("\n[2] 计算估值...")
            
            print("\n[3] 市场检测:")
            print("   市场类型: A股")
            print("   基准指数: 沪深300")
            print("   基准涨跌幅: +0.45%")
            
            print("\n[4] 前十持仓明细及贡献:")
            print(f"   {'股票代码':<10} {'股票名称':<12} {'占比':<8} {'涨跌幅':<10} {'贡献度':<10}")
            print(f"   {'-'*60}")
            
            demo_holdings = [
                ('600519', '贵州茅台', 9.5, 1.2, 0.114),
                ('000858', '五粮液', 8.8, 0.8, 0.070),
                ('000568', '泸州老窖', 8.5, 1.5, 0.128),
                ('002714', '牧原股份', 7.2, -0.5, -0.036),
                ('600809', '山西汾酒', 7.0, 0.9, 0.063),
                ('300750', '宁德时代', 6.8, 2.1, 0.143),
                ('000333', '美的集团', 6.5, 0.3, 0.020),
                ('000001', '平安银行', 5.2, -0.8, -0.042),
                ('002415', '海康威视', 4.8, 0.6, 0.029),
                ('000002', '万科A', 4.5, -1.2, -0.054),
            ]
            
            for code, name, ratio, change, contrib in demo_holdings:
                print(f"   {code:<10} {name:<12} {ratio:>6.2f}% {change:>+8.2f}% {contrib:>+8.3f}%")
            
            print(f"   {'-'*60}")
            print(f"   {'合计':<10} {'':<12} {68.8:>6.2f}% {'':<10} {+0.435:>+8.3f}%")
            
            print("\n[5] 仓位计算:")
            print("   前十持仓占比: 68.80%")
            print("   估算股票仓位: 88%")
            print("   剩余仓位: 19.20%")
            print("   剩余部分贡献: +0.45% × 19.20% = +0.086%")
            
            print("\n[6] 估值计算过程:")
            print("   前十持仓贡献: +0.435%")
            print("   剩余仓位贡献: +0.086%")
            print("   小计: +0.521%")
            print("   最终估值: +0.52%")
            
            print("\n" + "="*70)
            print("✅ 当日估值结果: +0.52%")
            print("="*70 + "\n")
            return
        else:
            collector = FundDataCollector()
            fund_name = collector.get_fund_name(args.fund_code)
            print_estimation_details(collector, args.fund_code, fund_name)
            return
    
    # 获取数据
    if args.demo:
        print("\n📊 使用演示数据模式...")
        comparison_data = generate_demo_data(args.fund_code, args.days)
        fund_name = f"演示基金-{args.fund_code}"
        
        # 演示模式下也支持显示逐日计算过程
        if args.show_daily_calc:
            print("\n📊 演示模式 - 逐日估值计算过程")
            print("="*70)
            print("\n说明：演示数据使用模拟的估值计算过程")
            print("="*70)
            
            for i, data in enumerate(comparison_data, 1):
                date = data['date']
                estimated = data['estimated_change']
                actual = data['actual_change']
                deviation = actual - estimated
                
                print(f"\n【第 {i} 天】{date}")
                print(f"  实际净值涨跌幅: {actual:+.2f}%")
                print(f"  估算涨跌幅: {estimated:+.2f}%")
                print(f"  偏差: {deviation:+.2f}%")
                print(f"  计算说明: 基于前十持仓加权计算 + 基准指数补齐")
                print(f"  {'-'*50}")
                
                # 每5天暂停一下
                if i % 5 == 0 and i < len(comparison_data):
                    print(f"\n  (已显示 {i}/{len(comparison_data)} 天，按 Enter 继续...)")
                    try:
                        input()
                    except:
                        pass
            
            print(f"\n{'='*70}")
            print(f"✅ 逐日估值计算完成")
            print(f"{'='*70}\n")
    else:
        print("\n📡 正在采集基金数据...")
        collector = FundDataCollector()
        fund_name = collector.get_fund_name(args.fund_code)
        
        try:
            comparison_data = collector.collect_comparison_data(
                args.fund_code, args.days, 
                show_daily_calc=args.show_daily_calc
            )
        except Exception as e:
            print(f"❌ 数据获取失败: {e}")
            print("💡 提示: 可以使用 --demo 参数运行演示模式")
            sys.exit(1)
    
    if not comparison_data:
        print("❌ 未能获取有效数据")
        sys.exit(1)
    
    print(f"✅ 成功获取 {len(comparison_data)} 天数据")
    
    # 进行分析
    print("\n🔬 正在分析基金经理行为...")
    analyzer = FundXrayAnalyzer(args.fund_code, fund_name)
    analyzer.load_data(comparison_data)
    
    # 计算周度指标
    metrics = analyzer.calculate_weekly_score(window_days=min(args.days, 20))
    
    # 获取每日详细数据
    daily_df = analyzer.get_daily_details()
    
    # 检测异常
    anomalies = analyzer.detect_anomalies(threshold=2.0)
    
    # 生成可视化报告
    visualizer = FundXrayVisualizer(output_dir=args.output_dir)
    
    # 打印命令行报告
    visualizer.print_console_report(
        args.fund_code, fund_name, metrics, daily_df, anomalies
    )
    
    # 生成图表
    if not args.no_chart:
        try:
            chart_file = visualizer.generate_chart(
                args.fund_code, fund_name, daily_df, metrics
            )
            print(f"\n📈 可视化图表已保存至: {chart_file}")
        except Exception as e:
            print(f"⚠️ 图表生成失败: {e}")
    
    print("\n✨ 分析完成!")
    
    # 根据折腾指数返回不同的退出码（便于脚本自动化）
    if metrics.zheteng_index >= 7:
        sys.exit(2)  # 高度折腾
    elif metrics.zheteng_index >= 5:
        sys.exit(1)  # 中度折腾
    else:
        sys.exit(0)  # 正常


if __name__ == '__main__':
    main()
