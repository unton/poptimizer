winget install --id="MongoDB.Server"
if %ERRORLEVEL% EQU -1978335189 exit /b 0
rem Ignore 'No applicable update found' return code
