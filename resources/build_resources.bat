@echo off

REM Incomplete translation of the adjacent bash script
REM Uses the tools in the Shotgun core
REM Does not do the SED step, outputs must be manually edited

REM The path to output all built .py files to:
set UI_PYTHON_PATH=..\python\app\ui

REM This is the edit which needs to be made in each file
REM sed -i "" -e "s/from PySide import/from tank.platform.qt import/g" -e "/# Created:/d" $UI_PYTHON_PATH/$4.py

set PYBASE=C:\Program Files\Shotgun\Python
path %PATH%;C:\Program Files\Shotgun\Qt\bin

echo "dialog.ui"
"%PYBASE%\python.exe" "%PYBASE%\bin\pyside-uic" --from-imports dialog.ui > dialog.py
REM sed
move dialog.py %UI_PYTHON_PATH%\

echo "list_item_widget.ui"
"%PYBASE%\python.exe" "%PYBASE%\bin\pyside-uic" --from-imports list_item_widget.ui > list_item_widget.py
REM sed
move list_item_widget.py %UI_PYTHON_PATH%\

echo "resources.qrc"
"%PYBASE%\bin\pyside-rcc.exe" resources.qrc > resources_rc.py
REM sed
move resources_rc.py %UI_PYTHON_PATH%\
