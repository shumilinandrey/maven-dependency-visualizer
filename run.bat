@echo off
cd /d "%~dp0"

python -m src.main ^
  -p org.apache.commons:commons-lang3 ^
  -r https://repo.maven.apache.org/maven2 ^
  -m url ^
  -v 1.2.3 ^
  -t y ^
  -d 321

pause