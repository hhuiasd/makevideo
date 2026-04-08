@echo off
chcp 65001 > nul

REM 视频快速混剪项目 - 手动参数执行
cd /d %~dp0

echo ==============================================
echo 视频快速混剪项目 - 手动参数模式
echo ==============================================
echo.
echo 请输入处理参数（单位：秒）
echo.

set /p skip_start="跳过视频开头秒数（默认1）: "
if "%skip_start%"=="" set skip_start=1

set /p skip_end="跳过视频结尾秒数（默认0）: "
if "%skip_end%"=="" set skip_end=0

set /p min_slice="最小切片时长秒数（默认3）: "
if "%min_slice%"=="" set min_slice=3

set /p max_slice="最大切片时长秒数（默认5）: "
if "%max_slice%"=="" set max_slice=5

echo.
echo ==============================================
echo 使用参数:
echo   跳过开头: %skip_start%秒
echo   跳过结尾: %skip_end%秒
echo   切片时长: %min_slice%-%max_slice%秒
echo ==============================================
echo.
echo 开始处理...
echo.

REM 运行Python脚本（使用自定义参数）
python main.py %skip_start% %skip_end% %min_slice% %max_slice%

echo.
echo ==============================================
echo 处理完成！
echo 输出文件位于 output 目录
echo ==============================================

echo.
echo 按任意键退出...
pause > nul
