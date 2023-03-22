# zzu_auto_sign
本项目仅用作学习目的。
现在不要求打卡，基本没用了。
用户信息在`config.yaml`中填写，包括百度地图的ak和百度智能云OCR的access_token。`history.yaml`用来记录打卡情况，便于推送，只会记录最近7天。支持多用户，仿照着`user0`的格式填写就行。

## pyinstaller 打包命令
``` shell
cd D:\zzu_sign_pkg
pipenv shell
pyinstaller -D -c -i "icon file path" --distpath="dist path" index.py
```

## OnePush
来自银弹大佬的推送包，详情请查看OnePush内的readme.md
