@echo off

REM The path to output all built .py files to:
REM UI_PYTHON_PATH=../python/app/ui
REM sed -i "" -e "s/from PySide import/from tank.platform.qt import/g" -e "/# Created:/d" $UI_PYTHON_PATH/$4.py

path %PATH%;C:\Python27\Scripts;C:\Python27\Lib\site-packages\PySide

:build_qt
setlocal
set name=%1
set name2=%2
REM do stuff
endlocal & set result=
goto :eof

:build_ui

:build_res


echo "dialog.ui"
pyside-uic --from-imports dialog.ui > dialog.py
REM sed

echo "list_item_widget.ui"
pyside-uic --from-imports list_item_widget.ui > list_item_widget.py
REM sed

pyside-rcc resources.qrc > resources_rc
REM sed
