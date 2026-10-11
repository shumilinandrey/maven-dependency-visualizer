@echo off
cd /d "%~dp0"

python -m src.main -p 123 ^
  -r https://github.com ^
  -m url ^
  -v 1.2.3 ^
  -t y ^
  -d 321

pause