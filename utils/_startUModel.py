import subprocess
import os
from configparser import BasicInterpolation, ConfigParser


config = ConfigParser(interpolation=BasicInterpolation())
config.read('settings.ini')

VAL_KEY = config["VALORANT"]["UE_AES"]
VAL_PAKS_PATH = config["VALORANT"]["PATH"] + "\live\ShooterGame\Content\Paks"
VAL_UMODEL_EXE = os.path.join(os.getcwd(), "tools", "umodel.exe")


def runUmodel():
    subprocess.call([
        VAL_UMODEL_EXE,
        f"-path={VAL_PAKS_PATH}",
        f"-game=valorant",
        f"-aes={VAL_KEY}",
    ])


runUmodel()
