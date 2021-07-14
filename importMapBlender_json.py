from math import *
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


# TODO FIX THE LOGGER
# TODO FIX NODE POSITIONS

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
SELECTED_MAP = config["VALORANT"]["MAP"]

WHITE_RGB = (1, 1, 1, 1)


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

    if logger.handlers.__len__() == 0:
        logger.addHandler(ch)
        logger.addHandler(fh)

try:
    sys.path.append(CWD.__str__())
    from utils import _umapList
    from utils import blenderUtils
    from utils import common

    importlib.reload(_umapList)
    importlib.reload(blenderUtils)
    importlib.reload(common)
except:
    logger.critical("Failed to load the utilities")


def cacheCheck():
    CWD.joinpath("export", "Scenes").mkdir(parents=True, exist_ok=True)

    # Check if settings.ini file set up correctly.
    # If not break the loop
    if VAL_PATH == "":
        logger.critical("You didn't setup your 'settings.ini' file!")
        return False

    if checkExtracted(VAL_EXPORT_FOLDER):
        logger.info("JSONs are already extracted")
    else:
        logger.warning("JSONs are not found, starting exporting!")
        # Extract JSONs
        extractJSONs()

        engineContent = CWD.joinpath("export", "Engine", "Content")
        engineF = CWD.joinpath("export", "Engine")

        # for dir in engineContent.iterdir():
        #     for f in dir.iterdir():
        #         oPath = f.__str__()
        #         nPath = oPath.replace("Content", "").replace("\\\\", "\\")

        #         yo = Path(nPath).parent
        #         yo.mkdir(parents=True, exist_ok=True)
        #         # os.chdir(nPath)
        #         # logger.info(f"{oPath} , {nPath}")
        #         try:
        #             f.rename(nPath)
        #         except:
        #             pass

    # Check if everything is exported from uModel
    if checkExported(VAL_EXPORT_FOLDER):
        logger.info("Models are already extracted")
    else:
        logger.warning("Exports not found, starting exporting!")
        # Export Models
        exportAllModels()


def readJSON(f: str):
    # print(f)
    # "C:\Users\ogulc\Desktop\valorant\val-scripts\export\Game\Environment\Asset\Props\Floater\15\Floater_15_PotholeA.gltf"
    # "C:\Users\ogulc\Desktop\valorant\val-scripts\export\ShooterGame\Content\Environment\Asset\Props\Floater\15\Floater_15_PotholeA.gltf"
    # logger.warning(f.__str__())

    # WARNING - C:\Users\ogulc\Desktop\valorant\val-scripts\export\Engine\Content\EngineMaterials\DefaultMaterial.json
    # WARNING - C:\Users\ogulc\Desktop\valorant\val-scripts\export\Engine\Content\Content\EngineMaterials\DefaultMaterial.json

    # if "\\Engine" in f.__str__():
    #     f = f.__str__().replace("\Engine", "\\Engine\\Content")
    #     if "ContentMaterials" in f:
    #         f = f.replace("Engine\\ContentMaterials", "EngineMaterials")

    # logger.warning(f.__str__())

    with open(f, 'r') as jsonFile:
        data = jsonFile.read()
        return json.loads(data)

        # logger.warning(f.__str__())


def checkImportable(object):
    # Check if entity has a loadable object
    if object["Type"] == "StaticMeshComponent" or object["Type"] == "InstancedStaticMeshComponent":
        if "StaticMesh" in object["Properties"]:
            if object["Properties"]["StaticMesh"] is not None:
                # Ensure only Visible objects are loaded
                if "bVisible" in object["Properties"]:
                    if object["Properties"]["bVisible"]:
                        return True
                    else:
                        return False
                else:
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
    a = CWD.joinpath("export", os.path.splitext(object["Properties"]["StaticMesh"]["ObjectPath"])[0].strip("/")).__str__()
    # print(a)
    b = a.replace("ShooterGame\Content", "Game")

    return b
    # return CWD.joinpath("export", os.path.splitext(object["Properties"]["StaticMesh"]["ObjectPath"])[0].strip("/")).__str__()


def getObjectname(object):

    # logger.info(object)
    return Path(object["Properties"]["StaticMesh"]["ObjectPath"]).stem


def getFullPath(mat: dict):
    matPath = os.path.splitext(mat["ObjectPath"])[0].strip("/")
    matPathFull = CWD.joinpath("export", matPath).__str__() + ".json"
    matPathFull = matPathFull.replace("ShooterGame\Content", "Game")
    return matPathFull


def getMatName(mat: dict):
    return Path(os.path.splitext(mat["ObjectPath"])[0].strip("/")).name


def createNode(material: bpy.types.Material, lookFor: str = "", nodeName: str = "", label: str = "", pos: list = False) -> bpy.types.ShaderNode:
    # Vertex Node

    try:
        node = material.node_tree.nodes[lookFor]
    except:
        node = material.node_tree.nodes.new(nodeName)
    if pos:
        node.location.x = pos[0]
        node.location.y = pos[1]
    if label != "":
        node.label = label

    return node


def getRGB(parameterValue: dict) -> tuple:
    return (
        parameterValue["ParameterValue"]["R"],
        parameterValue["ParameterValue"]["G"],
        parameterValue["ParameterValue"]["B"],
        parameterValue["ParameterValue"]["A"])


def setMaterial(byoMAT: bpy.types.Material, matJSON: dict, override: bool = False):
    # aem is ao emission and misc
    # mrs is metallic roughness and specular

    # byoMAT.node_tree.nodes.new('ShaderNodeGroup')

    byoMAT.use_nodes = True
    byoMAT.name = matJSON[0]["Name"]
    bsdf = byoMAT.node_tree.nodes["Principled BSDF"]

    defValue = 0.100
    bsdf.inputs["Specular"].default_value = defValue
    bsdf.inputs["Metallic"].default_value = defValue

    Diffuse_Map = False
    Diffuse_A_Map = False
    Diffuse_B_Map = False
    Diffuse_B_Low_Map = False

    MRA_MAP = False
    MRA_MAP_A = False
    MRA_MAP_B = False
    MRA_blendToFlat = False

    RGBA_MAP = False
    RGBA_MASK_COLOR = "R"
    MASK_MAP = False
    IMPACT_MAP = False

    Normal_Map = False
    Normal_A_Map = False
    Normal_B_Map = False

    # Blend_Power = False

    Diffuse_Alpha_Threshold = False
    # Diffuse_Clip_Value = False
    # Diffuse_Alpha_Emission = False
    # DFEmi = False

    DF_ALPHA = False
    usesAlpha = False

    isEmissive = False

    if override:
        imgNodePositionX = -1900.0

    else:
        imgNodePositionX = -1600.0

    vertexNode = createNode(material=byoMAT, lookFor="Vertex Color", nodeName="ShaderNodeVertexColor", label="Vertex Node", pos=[-1500.0, 1000])
    normalNode = createNode(material=byoMAT, lookFor="Normal Map", nodeName="ShaderNodeNormalMap", label="Normal Node", pos=[-400.0, -350])

    qo = 1400.0
    usedColor = (0, 0.6, 0.03)

    # Color Nodes
    Diffuse_Color = createNode(material=byoMAT, lookFor="RGB", nodeName="ShaderNodeRGB", label="DiffuseColor", pos=[-1500.0, 1400])
    byoMAT.node_tree.links.new(bsdf.inputs["Base Color"], Diffuse_Color.outputs["Color"])

    Layer_A_Tint = createNode(material=byoMAT, lookFor="RGB.001", nodeName="ShaderNodeRGB", label="Layer_A_TintColor", pos=[-1500.0, 1200])
    Layer_B_Tint = createNode(material=byoMAT, lookFor="RGB.002", nodeName="ShaderNodeRGB", label="Layer_B_TintColor", pos=[-1300.0, 1400])
    AO_Color = createNode(material=byoMAT, lookFor="RGB.003", nodeName="ShaderNodeRGB", label="AO_Color", pos=[-1300.0, 1200])
    Emissive_Mult = createNode(material=byoMAT, lookFor="RGB.004", nodeName="ShaderNodeRGB", label="Emissive_MultColor", pos=[-1100.0, 1400])
    Emissive_Color = createNode(material=byoMAT, lookFor="RGB.005", nodeName="ShaderNodeRGB", label="Emissive_Color", pos=[-1100.0, 1200])
    ML_Brightness = createNode(material=byoMAT, lookFor="RGB.006", nodeName="ShaderNodeRGB", label="ML_BrightnessColor", pos=[-900.0, 1400])

    # Mix Nodes
    Diffuse_Mix = createNode(material=byoMAT, lookFor="Mix", nodeName="ShaderNodeMixRGB", label="DiffuseColorMix", pos=[-600.0, 1600])
    Diffuse_Mix.blend_type = 'MIX'

    if Diffuse_Mix.inputs[1].links:
        byoMAT.node_tree.links.remove(Diffuse_Mix.inputs[1].links[0])

    Layer_A_Diffuse_Tint_Mix = createNode(material=byoMAT, lookFor="Mix.001", nodeName="ShaderNodeMixRGB", label="Layer_A_Diffuse_Tint_Mix", pos=[-600.0, 1400])
    Layer_B_Diffuse_Tint_Mix = createNode(material=byoMAT, lookFor="Mix.002", nodeName="ShaderNodeMixRGB", label="Layer_B_Diffuse_Tint_Mix", pos=[-600.0, 1200])
    Layer_Z_Diffuse_Tint_Mix = createNode(material=byoMAT, lookFor="Mix.003", nodeName="ShaderNodeMixRGB", label="Layer_Z_Diffuse_Tint_Mix", pos=[-600.0, 1000])
    Layer_Z_Diffuse_Tint_Mix.inputs[0].default_value = 1
    Layer_Z_Diffuse_Tint_Mix.blend_type = 'MULTIPLY'
    Normal_Mix = createNode(material=byoMAT, lookFor="Mix.004", nodeName="ShaderNodeMixRGB", label="NormalMix", pos=[-800.0, -500])

    Vertex_Math = createNode(material=byoMAT, lookFor="Math", nodeName="ShaderNodeMath", label="VertexMath", pos=[-800.0, -500])
    Vertex_Math.operation = 'MULTIPLY'
    Vertex_Math.inputs[1].default_value = 6

    Vertex_Mix = createNode(material=byoMAT, lookFor="Mix.005", nodeName="ShaderNodeMixRGB", label="MixWithAlpha", pos=[-800.0, -500])
    Vertex_Mix.blend_type = 'LINEAR_LIGHT'
    Vertex_Mix.inputs[0].default_value = 1
    Vertex_Mix.inputs[1].default_value = WHITE_RGB

    byoMAT.node_tree.links.new(Vertex_Mix.inputs[2], vertexNode.outputs["Color"])
    byoMAT.node_tree.links.new(Vertex_Math.inputs[0], Vertex_Mix.outputs["Color"])

    if "ScalarParameterValues" in matJSON[0]["Properties"]:
        for param in matJSON[0]["Properties"]["ScalarParameterValues"]:

            if param["ParameterInfo"]["Name"] == "Mask Blend Power":
                Blend_Power = param["ParameterValue"] * 0.01
            elif param["ParameterInfo"]["Name"] == "Opacity":
                pass

            elif param["ParameterInfo"]["Name"] == "NMINT A":
                pass
            elif param["ParameterInfo"]["Name"] == "NMINT B":
                pass

            elif param["ParameterInfo"]["Name"] == "normal_strength":
                pass
            elif param["ParameterInfo"]["Name"] == "Normal Mask Blend Power":
                pass
            elif param["ParameterInfo"]["Name"] == "Normal Mask Blend Mult":
                pass

            elif param["ParameterInfo"]["Name"] == "Metalness Reflection Intensity Adjustment":
                pass

            elif param["ParameterInfo"]["Name"] == "UVTiling X":
                pass
            elif param["ParameterInfo"]["Name"] == "UVTiling Y":
                pass
            elif param["ParameterInfo"]["Name"] == "UVOffsetMultiplier":
                pass
            elif param["ParameterInfo"]["Name"] == "RefractionDepthBias":
                pass

            elif param["ParameterInfo"]["Name"] == "Low Brightness":
                pass
            elif param["ParameterInfo"]["Name"] == "Min Light Brightness":
                pass
            elif param["ParameterInfo"]["Name"] == "Specular":
                pass
            elif param["ParameterInfo"]["Name"] == "Specular Lighting Mult":
                pass
            elif param["ParameterInfo"]["Name"] == "Speed X":
                pass
            elif param["ParameterInfo"]["Name"] == "Speed Y":
                pass
            elif param["ParameterInfo"]["Name"] == "U Tile":
                pass
            elif param["ParameterInfo"]["Name"] == "V Tile":
                pass
            elif param["ParameterInfo"]["Name"] == "UV Scale":
                pass

            elif param["ParameterInfo"]["Name"] == "Roughness Mult" or param["ParameterInfo"]["Name"] == "Roughness mult":
                pass
            elif param["ParameterInfo"]["Name"] == "Roughness Min" or param["ParameterInfo"]["Name"] == "Roughness_min":
                pass
            elif param["ParameterInfo"]["Name"] == "Roughness Max" or param["ParameterInfo"]["Name"] == "Roughness_max":
                pass
            elif param["ParameterInfo"]["Name"] == "Roughness A Mult":
                pass
            elif param["ParameterInfo"]["Name"] == "Roughness B Mult":
                pass
            elif param["ParameterInfo"]["Name"] == "Roughness A Min":
                pass
            elif param["ParameterInfo"]["Name"] == "Roughness A Max":
                pass
            elif param["ParameterInfo"]["Name"] == "Roughness B Min":
                pass
            elif param["ParameterInfo"]["Name"] == "Roughness B Max":
                pass

            else:
                pass
                # logger.warning(f"Found an unset ScalarParameterValue: {param['ParameterInfo']['Name']}")

    if "TextureParameterValues" in matJSON[0]["Properties"]:
        imgNodePositionY = 700.0
        imgNodeMargin = 300.0
        for texPROP in matJSON[0]["Properties"]["TextureParameterValues"]:
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            texGamePath = os.path.splitext(texPROP["ParameterValue"]["ObjectPath"])[0].strip("/")
            texGamePath = texGamePath.replace("ShooterGame/Content", "Game")
            # logger.info(texGamePath)
            texPath = CWD.joinpath("export", texGamePath).__str__() + ".tga"
            if Path(texPath).exists():
                textImageNode.image = bpy.data.images.load(texPath)

                # Set Image Node's Label, this helps a lot!
                textImageNode.label = texPROP["ParameterInfo"]["Name"]

                textImageNode.location.x = imgNodePositionX
                textImageNode.location.y = imgNodePositionY

                imgNodePositionY = imgNodePositionY - imgNodeMargin

                if texPROP["ParameterInfo"]["Name"] == "Diffuse":
                    textImageNode.image.alpha_mode = "CHANNEL_PACKED"
                    Diffuse_Map = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "Diffuse A":
                    textImageNode.image.alpha_mode = "CHANNEL_PACKED"
                    Diffuse_A_Map = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "Diffuse B":
                    textImageNode.image.alpha_mode = "CHANNEL_PACKED"
                    Diffuse_B_Map = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "Diffuse B Low":
                    textImageNode.image.alpha_mode = "CHANNEL_PACKED"
                    Diffuse_B_Low_Map = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "MRA":
                    textImageNode.image.colorspace_settings.name = "Linear"
                    MRA_MAP = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "MRA A":
                    textImageNode.image.colorspace_settings.name = "Linear"
                    MRA_MAP = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "MRA B":
                    textImageNode.image.colorspace_settings.name = "Linear"
                    MRA_MAP_B = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "RGBA":
                    textImageNode.image.colorspace_settings.name = "Linear"
                    RGBA_MAP = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "Mask Textuer":
                    textImageNode.image.colorspace_settings.name = "Linear"
                    MASK_MAP = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "Normal":
                    textImageNode.image.colorspace_settings.name = "Non-Color"
                    Normal_Map = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "Texture A Normal":
                    textImageNode.image.colorspace_settings.name = "Non-Color"
                    Normal_A_Map = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "Texture B Normal":
                    textImageNode.image.colorspace_settings.name = "Non-Color"
                    Normal_B_Map = textImageNode

                else:
                    pass
                    # logger.warning(f"Found an unset TextureParameterValue: {param['ParameterInfo']['Name']}")

    if "VectorParameterValues" in matJSON[0]["Properties"]:
        for param in matJSON[0]["Properties"]["VectorParameterValues"]:
            if param["ParameterInfo"]["Name"] == "DiffuseColor":
                Diffuse_Color.outputs[0].default_value = getRGB(param)
                Diffuse_Color.use_custom_color = True
                Diffuse_Color.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Layer A Tint":
                Layer_A_Tint.outputs[0].default_value = getRGB(param)
                Layer_A_Tint.use_custom_color = True
                Layer_A_Tint.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Layer B Tint":
                Layer_B_Tint.outputs[0].default_value = getRGB(param)
                Layer_B_Tint.use_custom_color = True
                Layer_B_Tint.color = usedColor
            elif param["ParameterInfo"]["Name"] == "AO color":
                AO_Color.outputs[0].default_value = getRGB(param)
                AO_Color.use_custom_color = True
                AO_Color.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Emissive Mult":
                Emissive_Mult.outputs[0].default_value = getRGB(param)
                Emissive_Mult.use_custom_color = True
                Emissive_Mult.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Emissive Color":
                Emissive_Color.outputs[0].default_value = getRGB(param)
                Emissive_Color.use_custom_color = True
                Emissive_Color.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Min Light Brightness Color":
                ML_Brightness.outputs[0].default_value = getRGB(param)
                ML_Brightness.use_custom_color = True
                ML_Brightness.color = usedColor
            else:
                pass
                # logger.warning(f"Found an unset VectorParameterValue: {param['ParameterInfo']['Name']}")

    if "BasePropertyOverrides" in matJSON[0]["Properties"]:
        if "ShadingModel" in matJSON[0]["Properties"]["BasePropertyOverrides"]:
            if matJSON[0]["Properties"]["BasePropertyOverrides"]["ShadingModel"] == "MSM_Unlit":
                isEmissive = True

        if "BlendMode" in matJSON[0]["Properties"]["BasePropertyOverrides"]:
            blendMode = matJSON[0]["Properties"]["BasePropertyOverrides"]["BlendMode"]
            if blendMode == "BLEND_Translucent" or blendMode == "BLEND_Masked":
                usesAlpha = "CLIP"
                byoMAT.blend_method = "CLIP"
                # byoMAT.blend_method = "CLIP"

        if "OpacityMaskClipValue" in matJSON[0]["Properties"]["BasePropertyOverrides"]:
            Diffuse_Alpha_Threshold = float(matJSON[0]["Properties"]["BasePropertyOverrides"]["OpacityMaskClipValue"])
            byoMAT.alpha_threshold = Diffuse_Alpha_Threshold

        if "StaticSwitchParameters" in matJSON[0]["Properties"]["BasePropertyOverrides"]:
            for param in matJSON[0]["Properties"]["BasePropertyOverrides"]["StaticSwitchParameters"]:
                if param["ParameterInfo"]["Name"] == "Use 2 Diffuse Maps":
                    pass
                if param["ParameterInfo"]["Name"] == "Blend To Flat":
                    pass
                if param["ParameterInfo"]["Name"] == "Blend To Flat MRA":
                    logger.info("fdasasnodnsafıdsaonfdsaıjkofğdpabfjsdaofbdsajofdsağbfdsao")
                    MRA_blendToFlat = True
                if param["ParameterInfo"]["Name"] == "Blend Roughness":
                    pass

    if "StaticParameters" in matJSON[0]["Properties"]:
        if "StaticComponentMaskParameters" in matJSON[0]["Properties"]:
            for param in matJSON[0]["Properties"]["StaticParameters"]["StaticComponentMaskParameters"]:
                if param["ParameterInfo"]["Name"] == "Mask":
                    if param["R"]:
                        RGBA_MASK_COLOR = "R"
                    if param["G"]:
                        RGBA_MASK_COLOR = "G"
                    if param["B"]:
                        RGBA_MASK_COLOR = "B"

    # // ------------------------------------------------------------------------

    if MRA_MAP:

        sepRGB_MRA_node = createNode(material=byoMAT, lookFor="", nodeName="ShaderNodeSeparateRGB", label="Seperate RGB_MRA", pos=[MRA_MAP.location.x + 300, MRA_MAP.location.y])
        byoMAT.node_tree.links.new(sepRGB_MRA_node.inputs['Image'], MRA_MAP.outputs["Color"])

        # byoMAT.node_tree.links.new(bsdf.inputs['Metallic'], sepRGB_MRA_node.outputs["R"])
        byoMAT.node_tree.links.new(bsdf.inputs['Roughness'], sepRGB_MRA_node.outputs["G"])
        byoMAT.node_tree.links.new(bsdf.inputs['Alpha'], sepRGB_MRA_node.outputs["B"])

        if MRA_blendToFlat:
            byoMAT.node_tree.links.new(sepRGB_MRA_node.inputs['Image'], MRA_MAP_A.outputs["Color"])
            if MRA_blendToFlat:
                logger.warning("yoyoyoyo")

                MRA_MIX = createNode(material=byoMAT, lookFor="asd", nodeName="ShaderNodeMixRGB", label="mix MRA", pos=[MRA_MAP_A.location.x + 500, MRA_MAP_A.location.y - 150])
                byoMAT.node_tree.links.new(MRA_MIX.inputs[0], vertexNode.outputs["Color"])
                byoMAT.node_tree.links.new(MRA_MIX.inputs['Color1'], MRA_MAP_A.outputs["Color"])
                MRA_MIX.inputs["Color2"].default_value = (0, 0, 0, 0)

                byoMAT.node_tree.links.new(sepRGB_MRA_node.inputs['Image'], MRA_MIX.outputs["Color"])
                byoMAT.node_tree.links.new(bsdf.inputs['Roughness'], sepRGB_MRA_node.outputs["G"])
            else:
                # byoMAT.node_tree.links.new(bsdf.inputs['Metallic'], sepRGB_MRA_M_node.outputs["R"])
                byoMAT.node_tree.links.new(bsdf.inputs['Roughness'], sepRGB_MRA_node.outputs["G"])
                # byoMAT.node_tree.links.new(bsdf.inputs['Alpha'], sepRGB_MRA_M_node.outputs["B"])

    if Diffuse_Map:

        # Layer_Z_Diffuse_Tint_Mix

        if Diffuse_Color.use_custom_color:
            byoMAT.node_tree.links.new(Layer_Z_Diffuse_Tint_Mix.inputs[1], Diffuse_Map.outputs["Color"])
            byoMAT.node_tree.links.new(Layer_Z_Diffuse_Tint_Mix.inputs[2], Diffuse_Color.outputs["Color"])
            byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], Layer_Z_Diffuse_Tint_Mix.outputs["Color"])

        else:
            byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], Diffuse_Map.outputs["Color"])
        if usesAlpha:
            byoMAT.node_tree.links.new(bsdf.inputs["Alpha"], Diffuse_Map.outputs["Alpha"])

    # ANCHOR Work here -------------
    if Diffuse_A_Map:

        byoMAT.node_tree.links.new(Vertex_Mix.inputs[1], Diffuse_A_Map.outputs["Alpha"])

        # Set Materials Diffuse to DiffuseMix Node
        byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], Diffuse_Mix.outputs["Color"])

        # DiffuseColorMix Node
        byoMAT.node_tree.links.new(Diffuse_Mix.inputs[0], Vertex_Math.outputs[0])                           # Pass Vertex Data
        byoMAT.node_tree.links.new(Diffuse_Mix.inputs[1], Layer_A_Diffuse_Tint_Mix.outputs["Color"])        # Pass Layer 1
        byoMAT.node_tree.links.new(Diffuse_Mix.inputs[2], Layer_B_Diffuse_Tint_Mix.outputs["Color"])        # Pass Layer 2

        # Layer_A_Diffuse_Tint_Mix Node
        byoMAT.node_tree.links.new(Layer_A_Diffuse_Tint_Mix.inputs[1], Layer_A_Tint.outputs["Color"])
        byoMAT.node_tree.links.new(Layer_A_Diffuse_Tint_Mix.inputs[2], Diffuse_A_Map.outputs["Color"])

        # Layer_B_Diffuse_Tint_Mix Node
        byoMAT.node_tree.links.new(Layer_B_Diffuse_Tint_Mix.inputs[1], Layer_B_Tint.outputs["Color"])
        if Diffuse_B_Map:
            byoMAT.node_tree.links.new(Layer_B_Diffuse_Tint_Mix.inputs[2], Diffuse_B_Map.outputs["Color"])
        else:
            Layer_B_Diffuse_Tint_Mix.inputs[1].default_value = WHITE_RGB

        Layer_A_Diffuse_Tint_Mix.inputs[0].default_value = 1
        Layer_B_Diffuse_Tint_Mix.inputs[0].default_value = 1
        Layer_A_Diffuse_Tint_Mix.blend_type = "MULTIPLY"
        Layer_B_Diffuse_Tint_Mix.blend_type = "MULTIPLY"

    if Normal_Map:
        byoMAT.node_tree.links.new(normalNode.inputs["Color"], Normal_Map.outputs["Color"])
        byoMAT.node_tree.links.new(bsdf.inputs['Normal'], normalNode.outputs['Normal'])

    if Normal_A_Map:
        # pass
        byoMAT.node_tree.links.new(Normal_Mix.inputs[0], Vertex_Math.outputs[0])

        byoMAT.node_tree.links.new(Normal_Mix.inputs[1], Normal_A_Map.outputs["Color"])

        if Normal_B_Map:
            byoMAT.node_tree.links.new(Normal_Mix.inputs[2], Normal_B_Map.outputs["Color"])
        else:
            Normal_Mix.inputs[1].default_value = WHITE_RGB

        byoMAT.node_tree.links.new(normalNode.inputs["Color"], Normal_Mix.outputs["Color"])
        byoMAT.node_tree.links.new(bsdf.inputs['Normal'], normalNode.outputs['Normal'])

    if RGBA_MAP:
        sepRGB_RGBA_node = createNode(material=byoMAT, lookFor="", nodeName="ShaderNodeSeparateRGB", label="Seperate RGB_RGBA", pos=[-390.0, -200])

        byoMAT.node_tree.links.new(sepRGB_RGBA_node.inputs[0], RGBA_MAP.outputs["Color"])

        byoMAT.node_tree.links.new(bsdf.inputs["Alpha"], sepRGB_RGBA_node.outputs[RGBA_MASK_COLOR])

    # Arrange nodes so they look cool
    # blenderUtils.arrangeNodes(byoMAT.node_tree)


def setMaterials(byo: bpy.types.Object, objectData: dict):
    # logger.info(f"setMaterials() | Object : {byo.name_full}")

    BYO_matCount = byo.material_slots.__len__()

    OG_objectData = readJSON(getFixedPath(objectData) + ".json")

    if "StaticMaterials" in OG_objectData[2]["Properties"]:
        for index, mat in enumerate(OG_objectData[2]["Properties"]["StaticMaterials"]):
            if mat["MaterialInterface"] is not None:
                matName = getMatName(mat["MaterialInterface"])
                if "WorldGridMaterial" not in matName:
                    matPath = getFullPath(mat["MaterialInterface"])
                    if Path(matPath).exists():
                        matData = readJSON(matPath)

                        try:
                            byoMAT = byo.material_slots[index].material
                            byoMAT.name = matName
                            setMaterial(byoMAT, matData)
                        except IndexError:
                            pass

    if "OverrideMaterials" in objectData["Properties"]:
        for index, mat in enumerate(objectData["Properties"]["OverrideMaterials"]):
            if mat is not None:
                matName = getMatName(mat)
                matPath = getFullPath(mat)
                if Path(matPath).exists():
                    matData = readJSON(matPath)

                    try:
                        byoMAT = byo.material_slots[index].material
                        byoMAT.name = matName
                        setMaterial(byoMAT, matData, override=True)
                    except IndexError:
                        pass
                else:
                    logger.warning(f"Can't find the material : {matPath}")


def importObject(object, objectIndex, umapName, mainScene):
    if object is not None:
        objName = getObjectname(object)
        objPath = getFixedPath(object) + ".gltf"

        if Path(objPath).exists():
            logger.info(f"[{objectIndex}] : Importing GLTF : {objPath}")
            with redirect_stdout(stdout):
                bpy.ops.import_scene.gltf(filepath=objPath, loglevel=5, merge_vertices=True)

            imported = bpy.context.active_object

            blenderUtils.objectSetProperties(imported, object)
            setMaterials(imported, object)

            # Move Object to UMAP Collection
            bpy.data.collections[umapName].objects.link(imported)
            mainScene.collection.objects.unlink(imported)

        else:
            logger.warning(f"Couldn't find Found GLTF : {objPath}")


def filterBS_Lights(obj):
    if "Properties" in obj:
        if "StaticMesh" in obj["Properties"]:
            if "ObjectName" in obj["Properties"]["StaticMesh"]:
                if "SuperGrid" not in obj["Properties"]["StaticMesh"]["ObjectName"] and "LightBlocker" not in obj["Properties"]["StaticMesh"]["ObjectName"]:
                    return True


def createLight(object: bpy.types.Object, index: int, collectionName: str, lightType: str = "POINT"):

    light_data = bpy.data.lights.new(name="", type=lightType)
    light_data.energy = 1000

    if lightType == "AREA":
        light_data.shape = "RECTANGLE"
        if "SourceWidth" in object["Properties"]:
            light_data.size = object["Properties"]["SourceWidth"] * 0.01
        if "SourceHeight" in object["Properties"]:
            light_data.size_y = object["Properties"]["SourceHeight"] * 0.01

    if lightType == "SPOT":
        if "OuterConeAngle" in object["Properties"]:
            light_data.spot_size = radians(object["Properties"]["OuterConeAngle"])

    # NOTE
    # Check these?
    #   "SourceRadius": 38.2382,
    #   "AttenuationRadius": 840.22626

    if "Intensity" in object["Properties"]:
        if "Intensity" in object["Properties"]:
            light_data.energy = object["Properties"]["Intensity"] * 0.1

    if "LightColor" in object["Properties"]:
        if "LightColor" in object["Properties"]:
            light_data.color = [
                abs((object["Properties"]["LightColor"]["R"]) / float(255)),
                abs((object["Properties"]["LightColor"]["G"]) / float(255)),
                abs((object["Properties"]["LightColor"]["B"]) / float(255))
            ]

    light_object = bpy.data.objects.new(name=object["Name"], object_data=light_data)

    blenderUtils.objectSetProperties(light_object, object)
    bpy.data.collections[collectionName].objects.link(light_object)


@timer
def main():
    cacheCheck()

    # Set renderer to Cycles so Eeeve doesn't scream.
    bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'GPU'

    # # // --------------------------------------------------
    # # Blender Loop

    for umapIndex, umap in enumerate(_umapList.MAPS[SELECTED_MAP.lower()]):
        blenderUtils.cleanUP()
        umapName = os.path.splitext(os.path.basename(umap))[0]
        umapPath = CWD.joinpath("export", umap.replace(".umap", ".json"))
        umapDATA = readJSON(umapPath)
        main_scene = bpy.data.scenes["Scene"]

        import_collection = bpy.data.collections.new(umapName)
        main_scene.collection.children.link(import_collection)

        logger.info(f"Processing UMAP : {umapName}")

        if "Lighting" in umapName:
            point_lights = bpy.data.collections.new("Point Lights")
            rect_lights = bpy.data.collections.new("Rect Lights")
            spot_lights = bpy.data.collections.new("Spot Lights")

            import_collection.children.link(point_lights)
            import_collection.children.link(rect_lights)
            import_collection.children.link(spot_lights)

            for objectIndex, object in enumerate(umapDATA):
                if object["Type"] == "InstancedStaticMeshComponent" or object["Type"] == "StaticMeshComponent":
                    if filterBS_Lights(object):
                        importObject(object, objectIndex, umapName, main_scene)

                if object["Type"] == "PointLightComponent":
                    createLight(object=object, index=objectIndex, collectionName="Point Lights", lightType="POINT")

                if object["Type"] == "RectLightComponent":
                    createLight(object=object, index=objectIndex, collectionName="Rect Lights", lightType="AREA")

                if object["Type"] == "SpotLightComponent":
                    createLight(object=object, index=objectIndex, collectionName="Spot Lights", lightType="SPOT")

        else:
            for objectIndex, object in enumerate(umapDATA):
                if checkImportable(object):
                    importObject(object, objectIndex, umapName, main_scene)

        # Anchor
        #  // ------------------------------------------
        #  // After this part saves the blend files, if working on the script, comment these out
        #  // ------------------------------------------

        # Save umap to .blend file
        bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", umapName).__str__() + ".blend")

    blenderUtils.cleanUP()
    bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", SELECTED_MAP.capitalize()).__str__() + ".blend")
    # Import other .blend files back!
    for umap in _umapList.MAPS[SELECTED_MAP]:
        umapName = os.path.splitext(os.path.basename(umap))[0]
        umapBlend = CWD.joinpath("export", "Scenes", umapName).__str__() + ".blend"

        sec = "\\Collection\\"
        obj = umapName

        fp = umapBlend + sec + obj
        dr = umapBlend + sec

        if Path(umapBlend).exists():
            # bpy.ops.wm.append(filepath=fp, filename=obj, directory=dr)
            bpy.ops.wm.link(filepath=fp, filename=obj, directory=dr)

    # ANCHOR
    # Set up Skybox
    # This is so junky omfg.
    bpy.context.scene.render.film_transparent = True
    worldMat = bpy.data.worlds['World']
    worldNodeTree = worldMat.node_tree

    if SELECTED_MAP.lower() == "ascent":
        skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M0\Skybox_M0_VeniceSky_DF.tga"
    elif SELECTED_MAP.lower() == "split":
        skyboxMapPath = r"export\Game\Environment\Bonsai\Asset\Props\Skybox\0\M0\Skybox_0_M0_DF.tga"
    elif SELECTED_MAP.lower() == "bind":
        # NOTE bind skybox is ugly as fuck! So I used
        # skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M0\Skybox_M0_DualitySky_DF.tga"
        skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M0\Skybox_M0_VeniceSky_DF.tga"
    elif SELECTED_MAP.lower() == "icebox":
        skyboxMapPath = r"export\Game\Environment\Port\WorldMaterials\Skydome\M1\Skydome_M1_DF.tga"
    elif SELECTED_MAP.lower() == "breeze":
        skyboxMapPath = r"export\Game\Environment\FoxTrot\Asset\Props\Skybox\0\M0\Skybox_0_M0_DF.tga"
    elif SELECTED_MAP.lower() == "haven":
        skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M3\Skybox_M3_DF.tga"
    elif SELECTED_MAP.lower() == "menu":
        skyboxMapPath = r"export\Game\Environment\Port\WorldMaterials\Skydome\M1\Skydome_M1_DF.tga"
    elif SELECTED_MAP.lower() == "poveglia":
        skyboxMapPath = r"export\Game\Environment\Port\WorldMaterials\Skydome\M1\Skydome_M1_DF.tga"
    else:
        skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M0\Skybox_M0_VeniceSky_DF.tga"

    ENV_MAP = os.path.join(CWD.__str__(), skyboxMapPath)

    ENV_MAP_NODE = createNode(worldMat, lookFor="Environment Texture", nodeName="ShaderNodeTexEnvironment", label="SkyboxTexture_VALORANT")
    ENV_MAP_NODE.image = bpy.data.images.load(ENV_MAP)

    BG_NODE = worldNodeTree.nodes["Background"]
    BG_NODE.inputs["Strength"].default_value = 3

    worldNodeTree.links.new(worldNodeTree.nodes["Background"].inputs['Color'], ENV_MAP_NODE.outputs["Color"])
    worldNodeTree.links.new(worldNodeTree.nodes['World Output'].inputs['Surface'], worldNodeTree.nodes["Background"].outputs["Background"])

    bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", SELECTED_MAP.capitalize()).__str__() + ".blend")


main()
