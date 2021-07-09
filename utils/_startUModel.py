import subprocess
import os
from configparser import BasicInterpolation, ConfigParser


config = ConfigParser(interpolation=BasicInterpolation())
config.read('settings.ini')

VAL_KEY = config["VALORANT"]["UE_AES"]
VAL_VERSION = config["VALORANT"]["UE_VERSION"]
VAL_PATH = config["VALORANT"]["PAKS"]
VAL_UMODEL_EXE = os.path.join(os.getcwd(), "tools", "umodel.exe")


def runUmodel():
    subprocess.call([
        VAL_UMODEL_EXE,
        f"-path={VAL_PATH}",
        f"-game=valorant",
        f"-aes={VAL_KEY}",
    ])


runUmodel()
