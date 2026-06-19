@echo off
setlocal

set "ROOT=%~dp0"
pushd "%ROOT%" >nul

echo [PathCopy] Installing dependencies, cleaning, and building PathCopy.exe...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\build_exe.ps1" -InstallDependencies -Clean
if errorlevel 1 goto :error

echo.
echo [PathCopy] Verifying build artifact...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%scripts\check_build.ps1" -ExePath "%ROOT%PathCopy.exe"
if errorlevel 1 goto :error

echo.
echo [PathCopy] Build completed successfully.
echo [PathCopy] Output: %ROOT%PathCopy.exe
goto :done

:error
echo.
echo [PathCopy] Build failed. See the output above for details.

:done
popd >nul
pause
endlocal
