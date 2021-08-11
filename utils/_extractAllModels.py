import subprocess
import os
from pathlib import Path
from configparser import BasicInterpolation, ConfigParser

CWD = Path(os.getcwd())

VAL_EXPORT_FOLDER = os.path.join(CWD, "export")
JSON_FOLDER = Path(os.path.join(CWD, "export", "JSONs"))
JSON_FOLDER.mkdir(parents=True, exist_ok=True)

config = ConfigParser(interpolation=BasicInterpolation())
config.read(os.path.join(CWD.__str__(), 'settings.ini'))

VAL_KEY = config["VALORANT"]["UE_AES"]
VAL_PATH = config["VALORANT"]["PATH"]
VAL_PAKS_PATH = config["VALORANT"]["PATH"] + "\live\ShooterGame\Content\Paks"
SELECTED_MAP = config["VALORANT"]["MAP"]


def exportAllModels():
    subprocess.call([CWD.joinpath("tools", "umodel.exe").__str__(),
                     f"-path={VAL_PAKS_PATH}",
                     f"-game=valorant",
                     f"-aes={VAL_KEY}",
                     "-export",
                     "*.uasset",
                     "-gltf",
                     "-nooverwrite",
                     f"-out={CWD.joinpath('export').__str__()}"])
    with open(CWD.joinpath("export", 'exported.yo').__str__(), 'w') as out_file:
        out_file.write("")


exportAllModels()
