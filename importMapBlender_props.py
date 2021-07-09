import io
import subprocess
import os
import json
import logging
import sys
import bpy
import importlib
from time import time
from contextlib import redirect_stdout
from pathlib import Path
from configparser import BasicInterpolation, ConfigParser

from bpy.types import ObjectConstraints


# // ------------------------------------
#

stdout = io.StringIO()
os.system("cls")
sys.dont_write_bytecode = True


CWD = Path(bpy.context.space_data.text.filepath).parent
VAL_EXPORT_FOLDER = os.path.join(CWD, "export")

config = ConfigParser(interpolation=BasicInterpolation())
config.read(os.path.join(CWD.__str__(), 'settings.ini'))

VAL_KEY = config["VALORANT"]["UE_AES"]
VAL_VERSION = config["VALORANT"]["UE_VERSION"]
VAL_PATH = config["VALORANT"]["PATH"]
VAL_PAKS_PATH = config["VALORANT"]["PAKS"]

# // ------------------------------------
# Setup Logging

# Reset old Log File
LOGFILE = os.path.join(CWD, "yo.log")

if Path(LOGFILE).exists():
    with open(LOGFILE, "r+") as f:
        f.truncate(0)

try:
    logger
except NameError:
    # create logger with 'spam_application'
    logger = logging.getLogger("yo")
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(LOGFILE)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    # logger.addHandler(fh)
    if logger.handlers.__len__() == 0:
        logger.addHandler(ch)


# for name in ('blender_id', 'blender_cloud'):
#     logging.getLogger(name).setLevel(logging.DEBUG)

# def register():
#     pass

# logging.basicConfig(level=logging.INFO,
#                     format='%(name)s - %(levelname)s - %(message)s')

# # ch = logging.StreamHandler()
# # ch.setLevel(logging.INFO)
# logger = logging.getLogger(__name__)

try:
    sys.path.append(CWD.__str__())
    from utils import _umapList
    from utils import blenderUtils
    from utils import common

    importlib.reload(_umapList)
    importlib.reload(blenderUtils)
    importlib.reload(common)

except:
    print("An exception occurred")


def getFiles(folderpath: str, format: str, recursive=False):
    """
    Args:
        folderpath (str): folder path get files
        param2 (str): file format to search
        recursive? (bool): default: False
    Returns:
        list: Returns list of file paths
    """

    if recursive:
        paths = Path(folderpath).glob(f'**/*{format}')
    else:
        paths = Path(folderpath).glob(f'*{format}')
    for path in paths:
        yield path.absolute()


def findFile(fileName: str, fileList: list):
    for f in fileList:
        if fileName in f:
            return f


logger.info("Getting material infos...")
# TXTs = list(getFiles(CWD.__str__(), ".txt", recursive=True))


def readJSON(f: str):
    if "\\Engine" in f.__str__():
        f = f.__str__().replace("\Engine", "\\Engine\\Content")

    with open(f, 'r') as jsonFile:
        data = jsonFile.read()
        return json.loads(data)


def readFile(f):
    if "\\Engine" in f.__str__():
        f = f.__str__().replace("\Engine", "\\Engine\\Content")

    with open(f, "r") as f:
        return f.readlines()


def checkImportable(object):
    if object["Type"] == "StaticMeshComponent" or object["Type"] == "InstancedStaticMeshComponent":
        if "StaticMesh" in object["Properties"]:
            return True


def writeToJson(f, d):
    with open(os.path.join(CWD.__str__(), "errors", f"{f}.json"), 'w') as outfile:
        json.dump(d, outfile, indent=4)


def timer(func):
    # This function shows the execution time of
    # the function object passed
    def wrap_func(*args, **kwargs):
        t1 = time()
        result = func(*args, **kwargs)
        t2 = time()
        # print(f'Function {func.__name__!r} executed in {(t2-t1):.4f}s')
        logger.info(f'Function {func.__name__!r} executed in {(t2-t1):.3f}s')
        return result
    return wrap_func


def checkExported(f):
    if Path(f).joinpath("exported.yo").exists():
        return True
    else:
        return False


def exportAllModels():
    subprocess.call([CWD.joinpath("tools", "umodel.exe").__str__(),
                     f"-path={VAL_PAKS_PATH}",
                     f"-game=valorant",
                     f"-aes={VAL_KEY}",
                    #  "-pkg=*.uasset",
                     "-export",
                     "*.uasset",
                     "-gltf",
                     "-nooverwrite",
                     f"-out={CWD.joinpath('export').__str__()}"],
                    stderr=subprocess.DEVNULL)
    with open(CWD.joinpath("export", 'exported.yo').__str__(), 'w') as out_file:
        out_file.write("")


def extractJSONs():
    subprocess.call([CWD.joinpath("tools", "lina.exe").__str__(),
                     f"{VAL_PAKS_PATH}",
                     f"{VAL_KEY}",
                     f"{CWD.joinpath('export').__str__()}"])
    with open(CWD.joinpath('export', 'exported.jo').__str__(), 'w') as out_file:
        out_file.write("")


def checkExtracted(f):
    if Path(f).joinpath("exported.jo").exists():
        return True
    else:
        return False


def getFixedPath(object):
    return CWD.joinpath("export", os.path.splitext(object["Properties"]["StaticMesh"]["ObjectPath"])[0].strip("/")).__str__()


def getObjectname(object):
    return Path(object["Properties"]["StaticMesh"]["ObjectPath"]).stem


def getFullPath(mat: dict):
    matPath = os.path.splitext(mat["ObjectPath"])[0].strip("/")
    matPathFull = CWD.joinpath("export", matPath).__str__() + ".props.txt"
    return matPathFull


def getTexPath(path: str):
    path = path.replace(" ", "").replace("ParameterValue=Texture2D", "").replace("'", "").replace("\n", "").replace("/", "", 1)
    path = os.path.splitext(path)[0]
    newPath = CWD.joinpath("export", path).__str__() + ".tga"

    return newPath


def getMatName(mat: dict):
    return Path(os.path.splitext(mat["ObjectPath"])[0].strip("/")).name


def setMaterial(byoMAT: bpy.types.Material, matDATA: str):
    # Enable nodes
    byoMAT.use_nodes = True
    bsdf = byoMAT.node_tree.nodes["Principled BSDF"]

    logger.info(f"setMaterial() | {byoMAT.name_full}")

    GLASS = False

    DIFFUSE_MAP = False
    MRA_MAP = False
    NORMAL_MAP = False

    DIFFUSE_A_MAP = False
    DIFFUSE_B_MAP = False
    DIFFUSE_B_LOW_MAP = False

    NORMAL_A_MAP = False
    NORMAL_B_MAP = False

    A_TINT = False
    B_TINT = False
    AO_COLOR = False

    ALPHA = False
    ALPHA_CLIP = False

    USE_2_DIFFUSE = False
    USE_DIFFUSE_B_ON_LOW = False

    for i, line in enumerate(matDATA):

        if "ParameterInfo = { Name=Use Alternative Diffuse B on Low }" in line:
            USE_DIFFUSE_B_ON_LOW = True

        if "ParameterInfo = { Name=Diffuse }" in line:
            texPath = getTexPath(matDATA[i+1])
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            textImageNode.image = bpy.data.images.load(texPath)
            DIFFUSE_MAP = textImageNode
        if "ParameterInfo = { Name=Diffuse A }" in line:
            texPath = getTexPath(matDATA[i+1])
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            textImageNode.image = bpy.data.images.load(texPath)
            DIFFUSE_A_MAP = textImageNode
        if "ParameterInfo = { Name=Diffuse B }" in line:
            texPath = getTexPath(matDATA[i+1])
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            textImageNode.image = bpy.data.images.load(texPath)
            DIFFUSE_B_MAP = textImageNode
        if "ParameterInfo = { Name=Diffuse B Low }" in line:
            texPath = getTexPath(matDATA[i+1])
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            textImageNode.image = bpy.data.images.load(texPath)
            DIFFUSE_B_LOW_MAP = textImageNode
            if USE_DIFFUSE_B_ON_LOW:
                DIFFUSE_B_MAP = textImageNode
        if "ParameterInfo = { Name=Texture A Normal }" in line:
            texPath = getTexPath(matDATA[i+1])
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            textImageNode.image = bpy.data.images.load(texPath)
            NORMAL_A_MAP = textImageNode
        if "ParameterInfo = { Name=Texture B Normal }" in line:
            texPath = getTexPath(matDATA[i+1])
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            textImageNode.image = bpy.data.images.load(texPath)
            NORMAL_B_MAP = textImageNode
        if "ParameterInfo = { Name=MRA }" in line:
            texPath = getTexPath(matDATA[i+1])
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            textImageNode.image = bpy.data.images.load(texPath)
            MRA_MAP = textImageNode
        if "ParameterInfo = { Name=Normal }" in line:
            texPath = getTexPath(matDATA[i+1])
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            textImageNode.image = bpy.data.images.load(texPath)
            NORMAL_MAP = textImageNode
        if "ParameterInfo = { Name=Use 2 Diffuse Maps }" in line:
            USE_2_DIFFUSE = True

        if "BlendMode = BLEND_Masked (1)" in line or "BlendMode = BLEND_Translucent (2)" in line:
            ALPHA = True
        if "BlendMode = BLEND_Translucent (2)" in line:
            GLASS = True
        if "OpacityMaskClipValue =" in line and "bOverride_OpacityMaskClipValue" not in line:
            ALPHA_CLIP = float(line.replace(" ", "").replace("OpacityMaskClipValue=", ""))
        if "ParameterInfo = { Name=Diffuse A }" in line:
            texPath = getTexPath(matDATA[i+1])
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            textImageNode.image = bpy.data.images.load(texPath)
            DIFFUSE_MAP = textImageNode

    if not GLASS:
        # if DIFFUSE_A_MAP and DIFFUSE_B_MAP:
        #     mixNode = byoMAT.node_tree.nodes.new("ShaderNodeMixRGB")

        if DIFFUSE_A_MAP:
            byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], DIFFUSE_A_MAP.outputs['Color'])
        elif DIFFUSE_MAP:
            byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], DIFFUSE_MAP.outputs['Color'])
            if ALPHA:
                byoMAT.node_tree.links.new(bsdf.inputs['Alpha'], DIFFUSE_MAP.outputs['Color'])
        if MRA_MAP:
            sepRGB_node = byoMAT.node_tree.nodes.new("ShaderNodeSeparateRGB")
            invertNode = byoMAT.node_tree.nodes.new("ShaderNodeInvert")
            byoMAT.node_tree.links.new(sepRGB_node.inputs[0], MRA_MAP.outputs['Color'])
            byoMAT.node_tree.links.new(bsdf.inputs['Metallic'], sepRGB_node.outputs[2])
            byoMAT.node_tree.links.new(invertNode.inputs['Color'], sepRGB_node.outputs[1])
            byoMAT.node_tree.links.new(bsdf.inputs['Roughness'], invertNode.outputs["Color"])
            # byoMAT.node_tree.links.new(bsdf.inputs['Alpha'], sepRGB_node.outputs[0])

        if NORMAL_A_MAP and NORMAL_B_MAP:
            pass
        elif NORMAL_MAP:
            NORMAL_MAP.image.colorspace_settings.name = "Non-Color"
            normal_node = byoMAT.node_tree.nodes.new("ShaderNodeNormalMap")
            byoMAT.node_tree.links.new(normal_node.inputs["Color"], NORMAL_MAP.outputs['Color'])
            byoMAT.node_tree.links.new(bsdf.inputs['Normal'], normal_node.outputs["Normal"])
        if ALPHA_CLIP:
            byoMAT.blend_method = "CLIP"
            byoMAT.alpha_threshold = ALPHA_CLIP


def setMaterials(byo: bpy.types.Object, objectData: dict):
    # logger.info(f"setMaterials() | Object : {byo.name_full}")

    BYO_matCount = byo.material_slots.__len__()

    OG_objectData = readJSON(getFixedPath(objectData) + ".json")

    if "StaticMaterials" in OG_objectData[2]["Properties"]:
        for index, mat in enumerate(OG_objectData[2]["Properties"]["StaticMaterials"]):
            matName = getMatName(mat["MaterialInterface"])
            if "WorldGridMaterial" not in matName:
                matPath = getFullPath(mat["MaterialInterface"])
                matData = readFile(matPath)

                # byoMAT = byo.material_slots[mat["ImportedMaterialSlotName"]].material
                byoMAT = byo.material_slots[index].material
                byoMAT.name = matName
                setMaterial(byoMAT, matData)

    # if "OverrideMaterials" in objectData["Properties"]:
    #     for index, mat in enumerate(objectData["Properties"]["OverrideMaterials"]):
    #         if mat is not None:
    #             matName = getMatName(mat)
    #             matPath = getFullPath(mat)
    #             matData = readFile(matPath)

    #             try:
    #                 byoMAT = byo.material_slots[index].material
    #             except IndexError:
    #                 pass

    #             byoMAT.name = matName
    #             # logger.info(matName)
    #             setMaterial(byoMAT, matData)


@timer
def main():

    CWD.joinpath("export", "Scenes").mkdir(parents=True, exist_ok=True)

    # Check if settings.ini file set up correctly.
    # If not break the loop
    if VAL_PATH == "":
        logger.error("You didn't setup your 'settings.ini' file!")
        return False

    if checkExtracted(VAL_EXPORT_FOLDER):
        logger.info("JSONs are already extracted")
    else:
        logger.warning("JSONs are not found, starting exporting!")
        extractJSONs()

    # Check if everything is exported from uModel
    if checkExported(VAL_EXPORT_FOLDER):
        logger.info("Models are already extracted")
    else:
        logger.warning("Exports not found, starting exporting!")
        # Export Models
        exportAllModels()

    # # // --------------------------------------------------
    # # Blender Loop

    SELECTED_MAP = "bind"

    blenderUtils.cleanUP()
    for i, umap in enumerate(_umapList.MAPS[SELECTED_MAP]):
        # blenderUtils.cleanUP()
        umapName = os.path.splitext(os.path.basename(umap))[0]
        umapPath = CWD.joinpath("export", umap.replace(".umap", ".json"))
        umapDATA = readJSON(umapPath)

        # logger.info(umapName)
        # logger.info(umapName)

        # bpy.ops.scene.new(type="NEW")
        main_scene = bpy.data.scenes["Scene"]

        import_collection = bpy.data.collections.new(umapName)
        main_scene.collection.children.link(import_collection)

        logger.info(f"Processing UMAP : {umapName}")

        for i, object in enumerate(umapDATA):

            if checkImportable(object):
                if i < 20000000:

                    # logger.debug(object["Properties"]["StaticMesh"]["ObjectPath"])
                    objName = getObjectname(object)
                    objPath = getFixedPath(object) + ".gltf"

                    if "Shell_11_BathHouseC" == objName:
                        if Path(objPath).exists():
                            # print("importing : ", objPath)
                            logger.info(f"[{i}] : Importing GLTF : {objPath}")
                            with redirect_stdout(stdout):
                                bpy.ops.import_scene.gltf(filepath=objPath, loglevel=5, merge_vertices=True)

                            imported = bpy.context.active_object

                            blenderUtils.objectSetProperties(imported, object)
                            setMaterials(imported, object)

                            # Move Object to UMAP Collection
                            bpy.data.collections[umapName].objects.link(imported)
                            main_scene.collection.objects.unlink(imported)

                        else:
                            # print("Couldn't object's file : ", objPath)
                            logger.warning(f"Couldn't find Found GLTF : {objPath}")

        # Save to .blend file
    #     bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", umapName).__str__() + ".blend")

    # blenderUtils.cleanUP()
    # bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", SELECTED_MAP).__str__() + ".blend")
    # for umap in _umapList.MAPS[SELECTED_MAP]:
    #     umapName = os.path.splitext(os.path.basename(umap))[0]
    #     umapBlend = CWD.joinpath("export", "Scenes", umapName).__str__() + ".blend"

    #     sec = "\\Collection\\"
    #     obj = umapName

    #     fp = umapBlend + sec + obj
    #     dr = umapBlend + sec

    #     if Path(umapBlend).exists():
    #         # C:\Users\ogulc\Desktop\valorant\valpy\export\Scenes\Duality_Art_A.blend\Collection\
    #         bpy.ops.wm.link(filepath=fp, filename=obj, directory=dr)
    # bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", SELECTED_MAP).__str__() + ".blend")


main()
