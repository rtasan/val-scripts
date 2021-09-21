import traceback
import io
import subprocess
import os
import json
import logging
import sys
import bpy
import importlib
import addon_utils
from time import time
from contextlib import redirect_stdout
from pathlib import Path
from configparser import BasicInterpolation, ConfigParser
from math import *


# ------------------------------------
# SELECT THE MAP
SELECTED_MAP = "fracture"

"""
ascent
split
bind
icebox
breeze
haven
fracture
range
"""

# You can edit these if you know what you are doing :)
_TEXTURE_FORMAT = ".png"    # DDS, TGA, PNG
_SAVE_JSONS = False         # Saves JSON files for manual Checking
_APPEND = True              # Appends the umap collections if true, otherwise it'll "link"
_DEBUG = False              # When active, it won't save the maps as .blend files.
_FOR_UPLOAD = True          # True : Packs the textures inside Blender File
_PROP_CHECK = False         # ..


# ------------------------------------
# DONT TOUCH AFTER

# TODO Fix the node positions
# TODO Fix the logger
# TODO Add ability to import single .umap

stdout = io.StringIO()
os.system("cls")
sys.dont_write_bytecode = True

CWD = Path(bpy.context.space_data.text.filepath).parent
VAL_EXPORT_FOLDER = os.path.join(CWD, "export")
JSON_FOLDER = Path(os.path.join(CWD, "export", "JSONs"))
JSON_FOLDER.mkdir(parents=True, exist_ok=True)

config = ConfigParser(interpolation=BasicInterpolation())
config.read(os.path.join(CWD.__str__(), 'settings.ini'))

VAL_KEY = config["VALORANT"]["UE_AES"]
VAL_PAKS_PATH = config["VALORANT"]["PATH"]
WHITE_RGB = (1, 1, 1, 1)
BLACK_RGB = (0, 0, 0, 0)


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

    # logging.getLogger("UE4Parse").setLevel(logging.INFO)
    # create logger with 'spam_application'
    logger = logging.getLogger("yo")
    logger.setLevel(logging.INFO)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(LOGFILE)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger

    if logger.handlers.__len__() == 0:
        logger.addHandler(ch)
        logger.addHandler(fh)

try:
    sys.path.append(os.path.join(CWD.__str__()))
    sys.path.append(os.path.join(CWD.__str__(), "utils"))

    from utils import _umapList
    from utils import blenderUtils
    from utils import common
    from utils.UE4Parse.Objects.EUEVersion import EUEVersion
    from utils.UE4Parse.provider.Provider import Provider, FGame

    importlib.reload(_umapList)
    importlib.reload(blenderUtils)
    importlib.reload(common)
except Exception:
    traceback.print_exc()

# ----------------------------------------------------------------
# Utilities


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


def shorten_path(file_path, length):
    # Split the path into separate parts, select the last
    # 'length' elements and join them again
    return f'..\{Path(*Path(file_path).parts[-length:])}'


def save_json(p: str, d):
    with open(p, 'w') as jsonfile:
        json.dump(d, jsonfile, indent=4)


@timer
def UE4Parser(gamePath: str, aesKey: str, gameName: str = "ShooterGame", version: EUEVersion = EUEVersion.GAME_VALORANT) -> Provider:
    aeskeys = {Provider.mainGuid: aesKey}

    game = FGame()
    game.UEVersion = version
    # game.GameName = gameName

    provider = Provider(pak_folder=gamePath, GameInfo=game, caseinsensitive=False)
    provider.read_paks(aeskeys)

    return provider


def check_exported(f: str):
    if Path(f).joinpath("exported.yo").exists():
        return True
    else:
        return False


def check_cache():
    CWD.joinpath("export", "Scenes").mkdir(parents=True, exist_ok=True)

    # Check if everything is exported from uModel
    if check_exported(VAL_EXPORT_FOLDER):
        logger.info("Models are already extracted")
    else:
        logger.warning("Models are not found, starting exporting!")

        # Export Models
        export_models()


@timer
def export_models():
    subprocess.call([CWD.joinpath("tools", "umodel.exe").__str__(),
                     f"-path={VAL_PAKS_PATH}",
                     f"-game=valorant",
                     f"-aes={VAL_KEY}",
                     "-export",
                     "*.uasset",
                     "-gltf",
                     "-nooverwrite",
                     f"-{_TEXTURE_FORMAT.replace('.', '')}",
                     f"-out={CWD.joinpath('export').__str__()}"],
                    stderr=subprocess.DEVNULL)
    with open(CWD.joinpath("export", 'exported.yo').__str__(), 'w') as out_file:
        out_file.write("")


def is_importable(object):
    objectProperties = object["ExportValue"]

    importable_types = [
        "StaticMeshComponent",
        "InstancedStaticMeshComponent",
        "HierarchicalInstancedStaticMeshComponent"]

    BLACKLIST = ["navmesh"]

    if any(x == object["ExportType"] for x in importable_types):
        if "StaticMesh" in objectProperties:
            if type(objectProperties["StaticMesh"]) is dict:
                objPath = get_object_path(objectProperties)
                for blocked in BLACKLIST:
                    if blocked in objPath.lower():
                        return False
                return True

# ----------------------------------------------------------------
# Getters


def get_object_name(objectProperties):
    p = Path(objectProperties["StaticMesh"]["OuterIndex"]["ObjectName"]).stem
    return p


def get_object_path(objectProperties):
    return objectProperties["StaticMesh"]["OuterIndex"]["ObjectName"]


def get_fixed_path(objectProperties):
    a = CWD.joinpath("export", os.path.splitext(
        objectProperties["StaticMesh"]["OuterIndex"]["ObjectName"])[0].strip("/")).__str__()
    return a


def get_mat_name(mat: dict):
    # logger.info(mat)
    return Path(mat["OuterIndex"]["ObjectName"]).name


def get_mat_path(mat: dict):
    return mat["OuterIndex"]["ObjectName"]


def get_math_path_full(mat: dict):
    matPath = os.path.splitext(mat["OuterIndex"]["ObjectName"])[0].strip("/")
    matPathFull = CWD.joinpath("export", matPath).__str__()
    return matPathFull

# Blender utilities

def create_node(material: bpy.types.Material, lookFor: str = "", nodeName: str = "", label: str = "", pos: list = False) -> bpy.types.ShaderNode:
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


def get_rgb(pa: dict) -> tuple:
    return (
        pa["ParameterValue"]["R"],
        pa["ParameterValue"]["G"],
        pa["ParameterValue"]["B"],
        pa["ParameterValue"]["A"])


def set_node_position(node: bpy.types.Node, posX, posY):
    node.location.x = posX
    node.location.y = posY


def set_material(byoMAT: bpy.types.Material, matJSON_FULL: dict, override: bool = False):

    matJSON = matJSON_FULL["Exports"][0]["ExportValue"]

    byoMAT.use_nodes = True
    byoMAT.name = matJSON_FULL["Exports"][0]["ExportName"]
    BSDF_NODE = byoMAT.node_tree.nodes["Principled BSDF"]

    defValue = 0.100
    BSDF_NODE.inputs["Specular"].default_value = defValue
    BSDF_NODE.inputs["Metallic"].default_value = defValue

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

    P_texture = False

    USE_VERTEX_COLOR = False
    USE_MIN_LIGHT_BRIGHTNESS_COLOR = False
    USE_DIFFUSE_B_ALPHA = False

    # Blend_Power = False

    Diffuse_Alpha_Threshold = False
    # Diffuse_Clip_Value = False
    # Diffuse_Alpha_Emission = False
    # DFEmi = False

    DF_ALPHA = False
    usesAlpha = False

    isEmissive = False
    isAdditive = False

    set_node_position(BSDF_NODE, 800, 780)
    set_node_position(byoMAT.node_tree.nodes["Material Output"], 1100, 780)

    VERTEX_NODE = create_node(material=byoMAT, lookFor="Vertex Color", nodeName="ShaderNodeVertexColor", label="VERTEX_NODE", pos=[-1800.0, 900])
    NORMAL_NODE = create_node(material=byoMAT, lookFor="Normal Map", nodeName="ShaderNodeNormalMap", label="NORMAL_NODE", pos=[500.0, 150.0])

    qo = 1400.0
    usedColor = (0, 0.6, 0.03)

    # Color Nodes
    DIFFUSE_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB", nodeName="ShaderNodeRGB", label="DIFFUSE_COLOR_NODE", pos=[-2000.0, 1800])
    byoMAT.node_tree.links.new(
        BSDF_NODE.inputs["Base Color"], DIFFUSE_COLOR_NODE.outputs["Color"])

    LAYER_A_TINT_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB.001", nodeName="ShaderNodeRGB", label="LAYER_A_TINT_COLOR_NODE", pos=[-2000.0, 1600])
    LAYER_B_TINT_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB.002", nodeName="ShaderNodeRGB", label="LAYER_B_TINT_COLOR_NODE", pos=[-1800.0, 1800])
    AO_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB.003", nodeName="ShaderNodeRGB", label="AO_COLOR_NODE", pos=[-1800.0, 1600])
    EMISSIVE_MULT_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB.004", nodeName="ShaderNodeRGB", label="EMISSIVE_MULT_COLOR_NODE", pos=[-1600.0, 1800])
    EMISSIVE_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB.005", nodeName="ShaderNodeRGB", label="EMISSIVE_COLOR_NODE", pos=[-1600.0, 1600])
    ML_BRIGHTNESS_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB.006", nodeName="ShaderNodeRGB", label="ML_BRIGHTNESS_COLOR_NODE", pos=[-1400.0, 1800])
    LM_VERTEX_ONLY_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB.007", nodeName="ShaderNodeRGB", label="LM_VERTEX_ONLY_COLOR_NODE", pos=[-1400.0, 1600])
    GM_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB.008", nodeName="ShaderNodeRGB", label="GM_COLOR_NODE", pos=[-1200.0, 1800])
    DIFFUSE_MULT_COLOR_NODE = create_node(material=byoMAT, lookFor="RGB.009", nodeName="ShaderNodeRGB", label="DIFFUSE_MULT_COLOR_NODE", pos=[-1200.0, 1600])

    # Mix Nodes
    Diffuse_Mix = create_node(material=byoMAT, lookFor="Mix", nodeName="ShaderNodeMixRGB", label="DiffuseColorMix", pos=[-400.0, 1600])
    Diffuse_Mix.blend_type = 'MIX'

    if Diffuse_Mix.inputs[1].links:
        byoMAT.node_tree.links.remove(Diffuse_Mix.inputs[1].links[0])

    Layer_A_Diffuse_Tint_Mix = create_node(material=byoMAT, lookFor="Mix.001", nodeName="ShaderNodeMixRGB", label="Layer_A_Diffuse_Tint_Mix", pos=[-400.0, 2200])
    Layer_B_Diffuse_Tint_Mix = create_node(material=byoMAT, lookFor="Mix.002", nodeName="ShaderNodeMixRGB", label="Layer_B_Diffuse_Tint_Mix", pos=[-400.0, 2000])
    MinLight_Tint_Mix_NODE = create_node(material=byoMAT, lookFor="Mix.003", nodeName="ShaderNodeMixRGB", label="MinLight_Tint_Mix_NODE", pos=[-400.0, 1800])
    MinLight_Tint_Mix_NODE.inputs[0].default_value = 1
    MinLight_Tint_Mix_NODE.blend_type = 'MULTIPLY'
    NORMAL_MIX_NODE = create_node(material=byoMAT, lookFor="Mix.004", nodeName="ShaderNodeMixRGB", label="NORMAL_MIX_NODE", pos=[-400, 1600])
    NORMAL_MIX_NODE.blend_type = 'MIX'

    VERTEX_MATH_NODE = create_node(material=byoMAT, lookFor="Math", nodeName="ShaderNodeMath", label="VertexMath", pos=[-950.0, 800])
    VERTEX_MATH_NODE.operation = 'MULTIPLY'
    VERTEX_MATH_NODE.inputs[1].default_value = 6

    VERTEX_MIX_NODE = create_node(material=byoMAT, lookFor="Mix.005", nodeName="ShaderNodeMixRGB", label="MixWithAlpha", pos=[-1200.0, 800])
    VERTEX_MIX_NODE.blend_type = 'LINEAR_LIGHT'
    VERTEX_MIX_NODE.inputs[0].default_value = 1
    VERTEX_MIX_NODE.inputs[1].default_value = WHITE_RGB

    byoMAT.node_tree.links.new(VERTEX_MIX_NODE.inputs[2], VERTEX_NODE.outputs["Color"])
    byoMAT.node_tree.links.new(VERTEX_MATH_NODE.inputs[0], VERTEX_MIX_NODE.outputs["Color"])

    set_node_position(VERTEX_MATH_NODE, -270, 600)
    set_node_position(VERTEX_MIX_NODE, -500, 600)
    set_node_position(VERTEX_NODE, -800, 350)

    if "ScalarParameterValues" in matJSON:
        for param in matJSON["ScalarParameterValues"]:
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
                if _PROP_CHECK:
                    logger.warning(f"Found an unset ScalarParameterValue: {param['ParameterInfo']['Name']}")

    if override:
        imgNodePositionX = -1300.0
    else:
        imgNodePositionX = -1000.0
    if "TextureParameterValues" in matJSON:
        imgNodePositionY = 1300.0
        imgNodeMargin = 300.0
        for texPROP in matJSON["TextureParameterValues"]:
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            texGamePath = os.path.splitext(texPROP["ParameterValue"]["OuterIndex"]["ObjectName"])[0].strip("/")
            # logger.info(texGamePath)
            texPath = CWD.joinpath("export", texGamePath).__str__() + _TEXTURE_FORMAT
            if Path(texPath).exists():

                # AtlasLogo_0_M0_DF.png

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

                elif texPROP["ParameterInfo"]["Name"] == "Normal A":
                    textImageNode.image.colorspace_settings.name = "Non-Color"
                    Normal_A_Map = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "Texture A Normal":
                    textImageNode.image.colorspace_settings.name = "Non-Color"
                    Normal_A_Map = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "Texture B Normal":
                    textImageNode.image.colorspace_settings.name = "Non-Color"
                    Normal_B_Map = textImageNode

                elif texPROP["ParameterInfo"]["Name"] == "texture":
                    textImageNode.image.colorspace_settings.name = "Linear"
                    P_texture = textImageNode

                else:
                    if _PROP_CHECK:
                        logger.warning(f"Found an unset TextureParameterValue: {param['ParameterInfo']['Name']}")

    if "VectorParameterValues" in matJSON:
        for param in matJSON["VectorParameterValues"]:
            if param["ParameterInfo"]["Name"] == "DiffuseColor":
                DIFFUSE_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                DIFFUSE_COLOR_NODE.use_custom_color = True
                DIFFUSE_COLOR_NODE.color = usedColor
            elif param["ParameterInfo"]["Name"] == "DiffuseMultColor":
                DIFFUSE_MULT_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                DIFFUSE_MULT_COLOR_NODE.use_custom_color = True
                DIFFUSE_MULT_COLOR_NODE.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Layer A Tint":
                LAYER_A_TINT_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                LAYER_A_TINT_COLOR_NODE.use_custom_color = True
                LAYER_A_TINT_COLOR_NODE.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Layer B Tint":
                LAYER_B_TINT_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                LAYER_B_TINT_COLOR_NODE.use_custom_color = True
                LAYER_B_TINT_COLOR_NODE.color = usedColor
            elif param["ParameterInfo"]["Name"] == "AO color":
                AO_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                AO_COLOR_NODE.use_custom_color = True
                AO_COLOR_NODE.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Emissive Mult":
                EMISSIVE_MULT_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                EMISSIVE_MULT_COLOR_NODE.use_custom_color = True
                EMISSIVE_MULT_COLOR_NODE.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Emissive Color":
                EMISSIVE_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                EMISSIVE_COLOR_NODE.use_custom_color = True
                EMISSIVE_COLOR_NODE.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Min Light Brightness Color":
                ML_BRIGHTNESS_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                ML_BRIGHTNESS_COLOR_NODE.use_custom_color = True
                ML_BRIGHTNESS_COLOR_NODE.color = usedColor
            elif param["ParameterInfo"]["Name"] == "Lightmass-only Vertex Color":
                LM_VERTEX_ONLY_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                LM_VERTEX_ONLY_COLOR_NODE.use_custom_color = True
                LM_VERTEX_ONLY_COLOR_NODE.color = usedColor
            elif param["ParameterInfo"]["Name"] == "color":
                GM_COLOR_NODE.outputs[0].default_value = get_rgb(param)
                GM_COLOR_NODE.use_custom_color = True
                GM_COLOR_NODE.color = usedColor

            else:
                # pass
                if _PROP_CHECK:
                    logger.warning(f"Found an unset VectorParameterValue: {param['ParameterInfo']['Name']}")

    if "BasePropertyOverrides" in matJSON:
        if "ShadingModel" in matJSON["BasePropertyOverrides"]:
            if "MSM_Unlit" in matJSON["BasePropertyOverrides"]["ShadingModel"]:
                isEmissive = True

        if "BlendMode" in matJSON["BasePropertyOverrides"]:
            blendMode = matJSON["BasePropertyOverrides"]["BlendMode"]
            if "BLEND_Translucent" in blendMode or "BLEND_Masked" in blendMode:
                usesAlpha = "CLIP"
                byoMAT.blend_method = "CLIP"
                # byoMAT.blend_method = "CLIP"
            if "BLEND_Additive" in blendMode:
                isAdditive = True

        if "OpacityMaskClipValue" in matJSON["BasePropertyOverrides"]:
            Diffuse_Alpha_Threshold = float(
                matJSON["BasePropertyOverrides"]["OpacityMaskClipValue"])
            byoMAT.alpha_threshold = Diffuse_Alpha_Threshold

    if "StaticParameters" in matJSON:
        if "StaticSwitchParameters" in matJSON["StaticParameters"]:
            for param in matJSON["StaticParameters"]["StaticSwitchParameters"]:
                if param["ParameterInfo"]["Name"] == "Use 2 Diffuse Maps":
                    pass
                if param["ParameterInfo"]["Name"] == "Blend To Flat":
                    pass
                if param["ParameterInfo"]["Name"] == "Blend To Flat MRA":
                    # logger.info("fdasasnodnsafıdsaonfdsaıjkofğdpabfjsdaofbdsajofdsağbfdsao")
                    MRA_blendToFlat = True
                if param["ParameterInfo"]["Name"] == "Blend Roughness":
                    pass
                if param["ParameterInfo"]["Name"] == "Use Vertex Color":
                    USE_VERTEX_COLOR = True
                if param["ParameterInfo"]["Name"] == "Use Diffuse B Alpha":
                    USE_DIFFUSE_B_ALPHA = True
                if param["ParameterInfo"]["Name"] == "BaseColor as Roughness":
                    USE_BASECOLOR_AS_ROUGHNESS = True
                if param["ParameterInfo"]["Name"] == "Use 2 Normal Maps":
                    USE_2_NORMAL_MAPS = True
                if param["ParameterInfo"]["Name"] == "Use Min Light Brightness Color":
                    USE_MIN_LIGHT_BRIGHTNESS_COLOR = True

    if MRA_MAP:

        sepRGB_MRA_node = create_node(material=byoMAT, lookFor="", nodeName="ShaderNodeSeparateRGB", label="Seperate RGB_MRA", pos=[MRA_MAP.location.x + 300, MRA_MAP.location.y])
        byoMAT.node_tree.links.new(sepRGB_MRA_node.inputs['Image'], MRA_MAP.outputs["Color"])

        # byoMAT.node_tree.links.new(BSDF_NODE.inputs['Metallic'], sepRGB_MRA_node.outputs["R"])
        byoMAT.node_tree.links.new(BSDF_NODE.inputs['Roughness'], sepRGB_MRA_node.outputs["G"])
        byoMAT.node_tree.links.new(BSDF_NODE.inputs['Alpha'], sepRGB_MRA_node.outputs["B"])

        if MRA_blendToFlat:
            byoMAT.node_tree.links.new(sepRGB_MRA_node.inputs['Image'], MRA_MAP.outputs["Color"])
            # logger.warning("yoyoyoyo")
            MRA_MIX = create_node(material=byoMAT, lookFor="asd", nodeName="ShaderNodeMixRGB", label="mix MRA", pos=[MRA_MAP.location.x + 500, MRA_MAP.location.y - 150])
            MRA_MIX.inputs["Color2"].default_value = BLACK_RGB

            byoMAT.node_tree.links.new(MRA_MIX.inputs[0], VERTEX_NODE.outputs["Color"])
            byoMAT.node_tree.links.new(MRA_MIX.inputs['Color1'], MRA_MAP.outputs["Color"])
            if MRA_MAP_B:
                byoMAT.node_tree.links.new(MRA_MIX.inputs['Color2'], MRA_MAP_B.outputs["Color"])

            byoMAT.node_tree.links.new(sepRGB_MRA_node.inputs['Image'], MRA_MIX.outputs["Color"])
            byoMAT.node_tree.links.new(BSDF_NODE.inputs['Roughness'], sepRGB_MRA_node.outputs["G"])

            set_node_position(MRA_MIX, -500, 300)
            set_node_position(sepRGB_MRA_node, -270, 300)
        else:
            # byoMAT.node_tree.links.new(BSDF_NODE.inputs['Metallic'], sepRGB_MRA_M_node.outputs["R"])
            byoMAT.node_tree.links.new(BSDF_NODE.inputs['Roughness'], sepRGB_MRA_node.outputs["G"])
            # byoMAT.node_tree.links.new(BSDF_NODE.inputs['Alpha'], sepRGB_MRA_M_node.outputs["B"])

    if Diffuse_Map:

        # MinLight_Tint_Mix_NODE

        if DIFFUSE_COLOR_NODE.use_custom_color:
            byoMAT.node_tree.links.new(MinLight_Tint_Mix_NODE.inputs[1], Diffuse_Map.outputs["Color"])
            byoMAT.node_tree.links.new(MinLight_Tint_Mix_NODE.inputs[2], DIFFUSE_COLOR_NODE.outputs["Color"])
            byoMAT.node_tree.links.new(BSDF_NODE.inputs['Base Color'], MinLight_Tint_Mix_NODE.outputs["Color"])
        else:
            byoMAT.node_tree.links.new(BSDF_NODE.inputs['Base Color'], Diffuse_Map.outputs["Color"])
        if usesAlpha:
            byoMAT.node_tree.links.new(BSDF_NODE.inputs["Alpha"], Diffuse_Map.outputs["Alpha"])

        if USE_VERTEX_COLOR:
            byoMAT.node_tree.links.new(MinLight_Tint_Mix_NODE.inputs[2], LM_VERTEX_ONLY_COLOR_NODE.outputs["Color"])
            byoMAT.node_tree.links.new(MinLight_Tint_Mix_NODE.inputs[1], Diffuse_Map.outputs["Color"])

    # ANCHOR Work here -------------
    if Diffuse_A_Map:

        byoMAT.node_tree.links.new(VERTEX_MIX_NODE.inputs[1], Diffuse_A_Map.outputs["Alpha"])
        # Set Materials Diffuse to DiffuseMix Node
        byoMAT.node_tree.links.new(BSDF_NODE.inputs['Base Color'], Diffuse_Mix.outputs["Color"])

        # DiffuseColorMix Node
        # Pass Vertex Data
        byoMAT.node_tree.links.new(Diffuse_Mix.inputs[0], VERTEX_MATH_NODE.outputs[0])
        byoMAT.node_tree.links.new(Diffuse_Mix.inputs[1], Layer_A_Diffuse_Tint_Mix.outputs["Color"])        # Pass Layer 1
        byoMAT.node_tree.links.new(Diffuse_Mix.inputs[2], Layer_B_Diffuse_Tint_Mix.outputs["Color"])        # Pass Layer 2

        # Layer_A_Diffuse_Tint_Mix Node
        byoMAT.node_tree.links.new(Layer_A_Diffuse_Tint_Mix.inputs[1], LAYER_A_TINT_COLOR_NODE.outputs["Color"])
        byoMAT.node_tree.links.new(Layer_A_Diffuse_Tint_Mix.inputs[2], Diffuse_A_Map.outputs["Color"])

        # Layer_B_Diffuse_Tint_Mix Node
        byoMAT.node_tree.links.new(Layer_B_Diffuse_Tint_Mix.inputs[1], LAYER_B_TINT_COLOR_NODE.outputs["Color"])
        if Diffuse_B_Map:
            byoMAT.node_tree.links.new(Layer_B_Diffuse_Tint_Mix.inputs[2], Diffuse_B_Map.outputs["Color"])
        else:
            Layer_B_Diffuse_Tint_Mix.inputs[1].default_value = WHITE_RGB

        Layer_A_Diffuse_Tint_Mix.inputs[0].default_value = 1
        Layer_B_Diffuse_Tint_Mix.inputs[0].default_value = 1
        Layer_A_Diffuse_Tint_Mix.blend_type = "MULTIPLY"
        Layer_B_Diffuse_Tint_Mix.blend_type = "MULTIPLY"

        set_node_position(Layer_A_Diffuse_Tint_Mix, -270, 1250)
        set_node_position(Layer_B_Diffuse_Tint_Mix, -270, 890)

        if USE_MIN_LIGHT_BRIGHTNESS_COLOR:
            MinLight_Tint_Mix_NODE.blend_type = "MULTIPLY"
            MinLight_Tint_Mix_NODE.inputs[0].default_value = 1
            byoMAT.node_tree.links.new(MinLight_Tint_Mix_NODE.inputs["Color1"], Diffuse_Mix.outputs["Color"])
            byoMAT.node_tree.links.new(MinLight_Tint_Mix_NODE.inputs["Color2"], LM_VERTEX_ONLY_COLOR_NODE.outputs["Color"])
            byoMAT.node_tree.links.new(BSDF_NODE.inputs["Base Color"], MinLight_Tint_Mix_NODE.outputs["Color"])

            set_node_position(MinLight_Tint_Mix_NODE, 280, 1000)
            set_node_position(Diffuse_Mix, 50, 1080)
            set_node_position(LM_VERTEX_ONLY_COLOR_NODE, 50, 820)

            set_node_position(LAYER_A_TINT_COLOR_NODE, -500, 1300)
            set_node_position(LAYER_B_TINT_COLOR_NODE, -500, 950)

            set_node_position(Layer_A_Diffuse_Tint_Mix, -270, 1250)
            set_node_position(Layer_B_Diffuse_Tint_Mix, -270, 890)

        if USE_DIFFUSE_B_ALPHA and Diffuse_B_Map:
            byoMAT.node_tree.links.new(VERTEX_MIX_NODE.inputs[1], Diffuse_B_Map.outputs["Alpha"])

    if Normal_Map:
        byoMAT.node_tree.links.new(NORMAL_NODE.inputs["Color"], Normal_Map.outputs["Color"])
        byoMAT.node_tree.links.new(BSDF_NODE.inputs['Normal'], NORMAL_NODE.outputs['Normal'])

    if Normal_A_Map:
        if Normal_B_Map:
            byoMAT.node_tree.links.new(NORMAL_MIX_NODE.inputs[0], VERTEX_MATH_NODE.outputs[0])
            byoMAT.node_tree.links.new(NORMAL_MIX_NODE.inputs[1], Normal_A_Map.outputs["Color"])
            byoMAT.node_tree.links.new(NORMAL_MIX_NODE.inputs[2], Normal_B_Map.outputs["Color"])
            byoMAT.node_tree.links.new(NORMAL_NODE.inputs["Color"], NORMAL_MIX_NODE.outputs["Color"])
            byoMAT.node_tree.links.new(BSDF_NODE.inputs['Normal'], NORMAL_NODE.outputs['Normal'])
            set_node_position(NORMAL_MIX_NODE, 300.0, 150.0)
        else:
            byoMAT.node_tree.links.new(NORMAL_NODE.inputs["Color"], Normal_A_Map.outputs["Color"])
            byoMAT.node_tree.links.new(BSDF_NODE.inputs['Normal'], NORMAL_NODE.outputs['Normal'])

    if RGBA_MAP:
        sepRGB_RGBA_node = create_node(material=byoMAT, lookFor="", nodeName="ShaderNodeSeparateRGB", label="Seperate RGB_RGBA", pos=[-390.0, -200])
        byoMAT.node_tree.links.new(sepRGB_RGBA_node.inputs[0], RGBA_MAP.outputs["Color"])
        byoMAT.node_tree.links.new(BSDF_NODE.inputs["Alpha"], sepRGB_RGBA_node.outputs[RGBA_MASK_COLOR])

    if P_texture:
        byoMAT.node_tree.links.new(BSDF_NODE.inputs['Base Color'], P_texture.outputs["Color"])
        byoMAT.node_tree.links.new(BSDF_NODE.inputs["Alpha"], P_texture.outputs["Color"])

        if isAdditive:
            byoMAT.node_tree.links.new(BSDF_NODE.inputs["Emission"], P_texture.outputs["Color"])


def set_materials(byo: bpy.types.Object, objectName: str, objectPath: str, object_OG: dict, object: dict, objIndex: int, JSON_Folder: Path):
    # logger.info(f"set_materials() | Object : {byo.name_full}")

    objectProperties = object["ExportValue"]
    objectProperties_OG = object_OG["Exports"][2]["ExportValue"]
    if _SAVE_JSONS:
        matFolder = JSON_Folder.joinpath("Materials")
        matFolder.mkdir(exist_ok=True)

    # save_json(p=JSON_Folder.joinpath(objectName + "_OG" + ".json"), d=object_OG)

    if "StaticMaterials" in objectProperties_OG:
        for index, mat in enumerate(objectProperties_OG["StaticMaterials"]):
            if type(mat["MaterialInterface"]) is dict:
                matName = get_mat_name(mat["MaterialInterface"])
                # matName = mat["ImportedMaterialSlotName"]
                if "WorldGridMaterial" not in matName:
                    matPath = get_mat_path(mat["MaterialInterface"])
                    matPack = provider.get_package(matPath)

                    if matPack is not None:
                        matJSON_FULL = matPack.parse_package().get_dict()
                        if _SAVE_JSONS:
                            save_json(p=matFolder.joinpath(matName + "_OG" + ".json"), d=matJSON_FULL)
                        try:
                            byoMAT = byo.material_slots[index].material
                            set_material(byoMAT=byoMAT, matJSON_FULL=matJSON_FULL, override=False)
                            byoMAT.name = matName + "_YO"
                        except IndexError:
                            pass

    if "OverrideMaterials" in objectProperties:
        for index, mat in enumerate(objectProperties["OverrideMaterials"]):
            if type(mat) is dict:
                matPath = get_mat_path(mat)
                matPack = provider.get_package(matPath)
                matJSON_FULL = matPack.parse_package().get_dict()

                matJSON = matJSON_FULL["Exports"][0]["ExportValue"]
                matName = matJSON_FULL["Exports"][0]["ExportName"]

                # REVIEW
                if _SAVE_JSONS:
                    save_json(p=matFolder.joinpath(matName + "_OVR" + ".json"), d=matJSON_FULL)

                try:
                    byoMAT = byo.material_slots[index].material
                    set_material(byoMAT=byoMAT, matJSON_FULL=matJSON_FULL, override=True)
                    byoMAT.name = matName + "_OG"
                    # logger.info(f"[{objIndex}] : Setting Material (Override) : {matName}")

                except IndexError:
                    pass


def import_object(object, objectIndex, umap_name, mainScene):

    objectProperties = object["ExportValue"]
    objName = get_object_name(objectProperties)
    objPath = get_fixed_path(objectProperties) + ".gltf"

    crt_JSON_FOLDER = JSON_FOLDER.joinpath(umap_name, objName)
    crt_JSON_FOLDER.mkdir(parents=True, exist_ok=True)

    objCheck = bpy.data.objects.get(objName)

    if objCheck is None:
        if _SAVE_JSONS:
            save_json(p=crt_JSON_FOLDER.joinpath(objName + ".json"), d=objectProperties)

        if Path(objPath).exists():
            logger.info(f"[{objectIndex}] : Importing Model : {shorten_path(objPath, 4)}")
            with redirect_stdout(stdout):
                bpy.ops.import_scene.gltf(filepath=objPath, loglevel=5, merge_vertices=True)

            imported = bpy.context.active_object
            blenderUtils.objectSetProperties(imported, objectProperties)
            objGamePath = get_object_path(objectProperties)

            # "/Engine/BasicShapes/Plane"
            # "Engine/Content/BasicShapes/Plane"
            if "/Engine/" in objGamePath:
                objGamePath = objGamePath.replace("/Engine/", "Engine/Content/")

            objPack = provider.get_package(objGamePath)
            objJSON_OG = objPack.parse_package().get_dict()

            if _SAVE_JSONS:
                save_json(p=crt_JSON_FOLDER.joinpath(objName + "_OG" + ".json"), d=objJSON_OG)

            set_materials(byo=imported, objectName=objName, objectPath=objPath, object_OG=objJSON_OG, object=object, objIndex=objectIndex, JSON_Folder=crt_JSON_FOLDER)

            # Move Object to UMAP Collection
            bpy.data.collections[umap_name].objects.link(imported)
            mainScene.collection.objects.unlink(imported)

        else:
            logger.warning(f"Couldn't find Found GLTF : {objPath}")
    else:
        logger.info(f"[{objectIndex}] : Duplicate Model : {shorten_path(objPath, 4)}")

        # Old Method
        new_obj = objCheck.copy()
        blenderUtils.objectSetProperties(new_obj, objectProperties)
        bpy.data.collections[umap_name].objects.link(new_obj)


def create_light(object: dict, index: int, collectionName: str, lightType: str = "POINT"):

    light_data = bpy.data.lights.new(name="", type=lightType)
    light_data.energy = 1000

    if lightType == "AREA":
        light_data.shape = "RECTANGLE"
        if "SourceWidth" in object["ExportValue"]:
            light_data.size = object["ExportValue"]["SourceWidth"] * 0.01
        if "SourceHeight" in object["ExportValue"]:
            light_data.size_y = object["ExportValue"]["SourceHeight"] * 0.01

    if lightType == "SPOT":
        if "OuterConeAngle" in object["ExportValue"]:
            light_data.spot_size = radians(object["ExportValue"]["OuterConeAngle"])

    # NOTE
    # Check these?
    #   "SourceRadius": 38.2382,
    #   "AttenuationRadius": 840.22626

    if "Intensity" in object["ExportValue"]:
        if "Intensity" in object["ExportValue"]:
            light_data.energy = object["ExportValue"]["Intensity"] * 0.1

    if "LightColor" in object["ExportValue"]:
        if "LightColor" in object["ExportValue"]:
            light_data.color = [
                abs((object["ExportValue"]["LightColor"]["R"]) / float(255)),
                abs((object["ExportValue"]["LightColor"]["G"]) / float(255)),
                abs((object["ExportValue"]["LightColor"]["B"]) / float(255))
            ]

    light_object = bpy.data.objects.new(name=object["ExportName"], object_data=light_data)

    blenderUtils.objectSetProperties(light_object, object["ExportValue"])
    bpy.data.collections[collectionName].objects.link(light_object)


def remove_duplicate_mats():
    obj: bpy.types.Object
    matSlot: bpy.types.MaterialSlot

    for obj in bpy.data.objects:
        for matSlot in obj.material_slots:
            # Filter Duplicate materials
            if os.path.splitext(matSlot.name)[1]:
                unique_mat = bpy.data.materials.get(os.path.splitext(matSlot.name)[0])
                matSlot.material = unique_mat

    for material in bpy.data.materials:
        if not material.users:
            bpy.data.materials.remove(material)


def remove_duplicate_lights():
    tex: bpy.types.Image
    obj: bpy.types.Object
    mat_slot: bpy.types.MaterialSlot
    node: bpy.types.Node

    for obj in bpy.data.objects:
        for mat_slot in obj.material_slots:
            current_material = mat_slot.material
            if current_material is not None:
                mat_nodes = current_material.node_tree.nodes
                for node in mat_nodes:
                    # Check for Texture Node
                    if type(node) is bpy.types.ShaderNodeTexImage:
                        # Filter Duplicate materials
                        if os.path.splitext(node.image.name.replace(_TEXTURE_FORMAT, ""))[1]:
                            node.image = bpy.data.images.get(os.path.splitext(node.image.name)[0])

    for block in bpy.data.textures:
        if block.users == 0:
            bpy.data.textures.remove(block)

    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


def filter_objects(umap_DATA) -> list:
    objects = []
    for object in umap_DATA:
        if is_importable(object):
            objects.append(object)
    return objects


def set_hdr(selected_map: str, texture_format: str):
    # ANCHOR
    # Set up Skybox
    bpy.context.scene.render.film_transparent = True
    worldMat = bpy.data.worlds['World']
    worldNodeTree = worldMat.node_tree

    if selected_map.lower() == "ascent":
        skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M0\Skybox_M0_VeniceSky_DF" + texture_format
    elif selected_map.lower() == "split":
        skyboxMapPath = r"export\Game\Environment\Bonsai\Asset\Props\Skybox\0\M0\Skybox_0_M0_DF" + texture_format
    elif selected_map.lower() == "bind":
        # NOTE bind skybox is ugly as fuck! So I used
        # skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M0\Skybox_M0_DualitySky_DF"
        skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M0\Skybox_M0_VeniceSky_DF" + texture_format
    elif selected_map.lower() == "icebox":
        skyboxMapPath = r"export\Game\Environment\Port\WorldMaterials\Skydome\M1\Skydome_M1_DF" + texture_format
    elif selected_map.lower() == "breeze":
        skyboxMapPath = r"export\Game\Environment\FoxTrot\Asset\Props\Skybox\0\M0\Skybox_0_M0_DF" + texture_format
    elif selected_map.lower() == "haven":
        skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M3\Skybox_M3_DF" + texture_format
    elif selected_map.lower() == "menu":
        skyboxMapPath = r"export\Game\Environment\Port\WorldMaterials\Skydome\M1\Skydome_M1_DF" + texture_format
    elif selected_map.lower() == "poveglia":
        skyboxMapPath = r"export\Game\Environment\Port\WorldMaterials\Skydome\M1\Skydome_M1_DF" + texture_format
    else:
        skyboxMapPath = r"export\Game\Environment\Asset\WorldMaterials\Skybox\M0\Skybox_M0_VeniceSky_DF" + texture_format

    ENV_MAP = os.path.join(CWD.__str__(), skyboxMapPath)

    ENV_MAP_NODE = create_node(worldMat, lookFor="Environment Texture", nodeName="ShaderNodeTexEnvironment", label="SkyboxTexture_VALORANT")
    ENV_MAP_NODE.image = bpy.data.images.load(ENV_MAP)

    BG_NODE = worldNodeTree.nodes["Background"]
    BG_NODE.inputs["Strength"].default_value = 3

    worldNodeTree.links.new(worldNodeTree.nodes["Background"].inputs['Color'], ENV_MAP_NODE.outputs["Color"])
    worldNodeTree.links.new(worldNodeTree.nodes['World Output'].inputs['Surface'], worldNodeTree.nodes["Background"].outputs["Background"])

@timer
def import_umap(umap_PKG, umap_name: str, map_folder: Path, map_type: str):
    logger.info(f"Processing UMAP : {umap_name}")

    if map_type is "vfx" or map_type is "object":
        main_scene = bpy.data.scenes["Scene"]
        # Use the data directly, because why not.
        umap_DATA_FULL = umap_PKG.parse_package().get_dict()
        umap_DATA = umap_DATA_FULL["Exports"]
        # Save for debug purposes, has no use.
        if _SAVE_JSONS:
            save_json(p=map_folder.joinpath(umap_name + ".json"), d=umap_DATA_FULL)
        import_collection = bpy.data.collections.new(umap_name)
        main_scene.collection.children.link(import_collection)

        if map_type is "object":
            objectsToImport = filter_objects(umap_DATA)
            for objectIndex, object in enumerate(objectsToImport):
                import_object(object, objectIndex, umap_name, main_scene)

        if map_type is "vfx":
            # Add support for VFX Textures
            objectsToImport = filter_objects(umap_DATA)
            for objectIndex, object in enumerate(objectsToImport):
                import_object(object, objectIndex, umap_name, main_scene)

    if map_type is "lights":
        # Use the data directly, because why not.
        umapDATA_FULL = umap_PKG.parse_package().get_dict()
        umapDATA = umapDATA_FULL["Exports"]

        # Save for debug purposes, has no use.
        if _SAVE_JSONS:
            save_json(p=map_folder.joinpath(umap_name + ".json"), d=umapDATA_FULL)

        main_scene = bpy.data.scenes["Scene"]

        import_collection = bpy.data.collections.new(umap_name)
        main_scene.collection.children.link(import_collection)

        point_lights = bpy.data.collections.new("Point Lights")
        rect_lights = bpy.data.collections.new("Rect Lights")
        spot_lights = bpy.data.collections.new("Spot Lights")

        import_collection.children.link(point_lights)
        import_collection.children.link(rect_lights)
        import_collection.children.link(spot_lights)

        for objectIndex, object in enumerate(umapDATA):

            if object["ExportType"] == "PointLightComponent":
                create_light(object=object, index=objectIndex, collectionName="Point Lights", lightType="POINT")

            if object["ExportType"] == "RectLightComponent":
                create_light(object=object, index=objectIndex, collectionName="Rect Lights", lightType="AREA")

            if object["ExportType"] == "SpotLightComponent":
                create_light(object=object, index=objectIndex, collectionName="Spot Lights", lightType="SPOT")

    remove_duplicate_mats()
    remove_duplicate_lights()

    # ! Utility to pack
    if _FOR_UPLOAD:
        bpy.ops.file.pack_all()

    # ! Save umap to .blend file
    if not _DEBUG:
        bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", umap_name).__str__() + ".blend", compress=True)


def combine_umaps():

    # ! Import other .blend files back!
    for umap in _umapList.MAPS[SELECTED_MAP]:
        umap_name = os.path.splitext(os.path.basename(umap))[0]
        umap_blend_file = CWD.joinpath("export", "Scenes", umap_name).__str__() + ".blend"

        sec = "\\Collection\\"
        obj = umap_name

        fp = umap_blend_file + sec + obj
        dr = umap_blend_file + sec

        if Path(umap_blend_file).exists():

            if _APPEND:
                bpy.ops.wm.append(filepath=fp, filename=obj, directory=dr)
            else:
                bpy.ops.wm.link(filepath=fp, filename=obj, directory=dr)


def post_setup():
    # After UMaps are done;
    if not _DEBUG:
        bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", SELECTED_MAP.capitalize()).__str__() + ".blend", compress=True)

        # ! Clear everything
        blenderUtils.cleanUP()

        combine_umaps()

        remove_duplicate_mats()
        remove_duplicate_lights()

        set_hdr(selected_map=SELECTED_MAP, texture_format=_TEXTURE_FORMAT)

        # ! Utility to pack
        if _FOR_UPLOAD:
            bpy.ops.file.pack_all()

        # ! Save umap to .blend file
        bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", SELECTED_MAP.capitalize()).__str__() + ".blend", compress=True)


@timer
def main():
    check_cache()

    global provider
    provider = UE4Parser(VAL_PAKS_PATH, VAL_KEY)
    print(provider)

    # Set renderer to Cycles so Eeeve doesn't scream.
    bpy.context.scene.render.engine = 'BLENDER_WORKBENCH'
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.device = 'GPU'

    # --------------------------------------------------
    # Blender Loop

    MAP_FOLDER = CWD.joinpath("export", "Maps", SELECTED_MAP.capitalize())
    MAP_FOLDER.mkdir(parents=True, exist_ok=True)

    for umap in _umapList.MAPS[SELECTED_MAP.lower()]:
        blenderUtils.cleanUP()

        umap_name = os.path.splitext(os.path.basename(umap))[0]
        umap_package = provider.get_package(umap)

        if umap_package is not None:
            if "Lighting" in umap_name:
                import_umap(umap_PKG=umap_package, umap_name=umap_name, map_folder=MAP_FOLDER, map_type="lights")
            elif "VFX" in umap_name:
                import_umap(umap_PKG=umap_package, umap_name=umap_name, map_folder=MAP_FOLDER, map_type="vfx")
            else:
                import_umap(umap_PKG=umap_package, umap_name=umap_name, map_folder=MAP_FOLDER, map_type="object")

    # Create empty scene, import all umaps, remove duplicates, make skybox, pack, and save!
    post_setup()


if (2, 93, 0) > bpy.app.version:
    logger.warning(
        "Your version of Blender is not supported, update to 2.93 or higher.")
    logger.warning("https://www.blender.org/download/")
else:

    IS_GLTF_ENABLED = addon_utils.check('io_scene_gltf2')[0]

    if not IS_GLTF_ENABLED:
        addon_utils.enable("io_scene_gltf2", default_set=True)
        logger.info("Enabled : GLTF Addon!")

    main()
