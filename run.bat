@echo off
chcp 65001 >nul
title FundXray - 基金透视仪
color 0A

echo.
echo ============================================
echo    FundXray - 基金透视仪
echo    检测基金经理的"折腾"行为
echo ============================================
echo.

REM 检查 Python 是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo [1/3] 检查依赖...
REM 检查并安装依赖
pip show numpy >nul 2>&1
if errorlevel 1 (
    echo    正在安装依赖包...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo [错误] 依赖安装失败，请手动运行: pip install -r requirements.txt
        pause
        exit /b 1
    )
)
echo    依赖检查完成

echo.
echo [2/3] 请选择运行模式:
echo    1. 演示模式 (使用模拟数据)
echo    2. 分析真实基金 (需要输入基金代码)
echo    3. 显示估值计算详情
echo    4. 退出
echo.

set /p choice="请输入选项 (1/2/3/4): "

if "%choice%"=="1" goto demo
if "%choice%"=="2" goto real
if "%choice%"=="3" goto calc
if "%choice%"=="4" goto exit
goto invalid

:demo
echo.
echo [3/3] 启动演示模式...
echo.
echo 请选择演示内容:
echo    1. 显示折腾指数分析
echo    2. 显示估值计算过程
echo.
set /p demo_choice="请输入选项 (1/2): "

if "%demo_choice%"=="1" goto demo_analysis
if "%demo_choice%"=="2" goto demo_calc
goto demo_analysis

:demo_analysis
echo    正在生成演示数据...
echo.
python fundxray.py 110011 --demo --no-chart
echo.
pause
goto end

:demo_calc
echo    正在显示估值计算过程...
echo.
python fundxray.py 110011 --demo --show-calc
echo.
pause
goto end

:real
echo.
set /p fund_code="请输入基金代码 (6位数字，如 110011): "

REM 验证基金代码
echo %fund_code%| findstr /R "^[0-9][0-9][0-9][0-9][0-9][0-9]$" >nul
if errorlevel 1 (
    echo [错误] 基金代码必须是6位数字！
    pause
    goto end
)

echo.
echo [3/3] 正在分析基金 %fund_code%...
echo.
echo 请选择分析模式:
echo    1. 完整分析（含逐日估值计算过程）
echo    2. 快速分析（仅显示结果）
echo.
set /p analysis_choice="请输入选项 (1/2): "

echo.
echo    正在获取数据，请稍候...
echo.

if "%analysis_choice%"=="2" goto quick_analysis

REM 完整分析 - 显示逐日估值计算过程
python fundxray.py %fund_code% --show-daily-calc --no-chart

goto analysis_done

:quick_analysis
REM 快速分析
python fundxray.py %fund_code% --no-chart

:analysis_done
if errorlevel 2 (
    echo.
    echo [警告] 检测到高度折腾行为！建议密切关注。
) else if errorlevel 1 (
    echo.
    echo [提示] 检测到中度操作痕迹，建议定期关注。
) else (
    echo.
    echo [提示] 基金经理操作正常，适合长期持有。
)

echo.
pause
goto end

:calc
echo.
set /p fund_code="请输入基金代码 (6位数字，如 110011): "

REM 验证基金代码
echo %fund_code%| findstr /R "^[0-9][0-9][0-9][0-9][0-9][0-9]$" >nul
if errorlevel 1 (
    echo [错误] 基金代码必须是6位数字！
    pause
    goto end
)

echo.
echo [3/3] 正在计算估值详情 %fund_code%...
echo    正在获取数据，请稍候...
echo.

python fundxray.py %fund_code% --show-calc

echo.
pause
goto end

:invalid
echo [错误] 无效选项，请重新运行
pause
goto end

:exit
echo.
echo 感谢使用 FundXray！
timeout /t 2 >nul
goto end

:end
