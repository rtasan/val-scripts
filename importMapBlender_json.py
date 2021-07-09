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

if 'logger' not in globals():
    # create logger with 'spam_application'
    logger = logging.getLogger('yo')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(LOGFILE)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    # logger.addHandler(fh)
    logger.addHandler(ch)


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


def readJSON(f: str):
    if "\\Engine" in f.__str__():
        f = f.__str__().replace("\Engine", "\\Engine\\Content")

    with open(f, 'r') as jsonFile:
        data = jsonFile.read()
        return json.loads(data)



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


# This is WIP
def setMaterial(byoMAT: bpy.types.Material, matJSON: dict, objectName: str):
    logger.info("Running : setMaterial()")

    # byoMAT.node_tree.nodes.new('ShaderNodeGroup')

    byoMAT.use_nodes = True
    byoMAT.name = matJSON[0]["Name"]
    bsdf = byoMAT.node_tree.nodes["Principled BSDF"]

    Diffuse_Map = False
    Diffuse_A_Map = False
    Diffuse_B_Map = False

    Normal_Map = False
    Normal_A_Map = False
    Normal_B_Map = False
    Diffuse_B_Low_Map = False

    Blend_Power = False

    Diffuse_Alpha_Threshold = False
    Diffuse_Clip_Value = False
    Diffuse_Alpha_Emission = False
    DFEmi = False

    Layer_A_Tint = False
    Layer_B_Tint = False
    AO_Color = False

    if "ScalarParameterValues" in matJSON[0]["Properties"]:
        for param in matJSON[0]["Properties"]["ScalarParameterValues"]:
            if param["ParameterInfo"]["Name"] == "Mask Blend Power":
                Blend_Power = param["ParameterValue"] * 0.01

    # logger.info(f"Setting Material : {objectName}")
    if "TextureParameterValues" in matJSON[0]["Properties"]:
        for texPROP in matJSON[0]["Properties"]["TextureParameterValues"]:
            textImageNode = byoMAT.node_tree.nodes.new('ShaderNodeTexImage')
            texGamePath = os.path.splitext(texPROP["ParameterValue"]["ObjectPath"])[0].strip("/")
            texPath = CWD.joinpath("export", texGamePath).__str__() + ".tga"
            textImageNode.image = bpy.data.images.load(texPath)

            if texPROP["ParameterInfo"]["Name"] == "Diffuse":
                Diffuse_Map = textImageNode
            if texPROP["ParameterInfo"]["Name"] == "Diffuse A":
                Diffuse_A_Map = textImageNode
            if texPROP["ParameterInfo"]["Name"] == "Diffuse B":
                Diffuse_B_Map = textImageNode
            if texPROP["ParameterInfo"]["Name"] == "Diffuse B Low":
                Diffuse_B_Low_Map = textImageNode
            if texPROP["ParameterInfo"]["Name"] == "RGBA":
                Diffuse_Map = textImageNode

            # yooooooooooooooooo
            # -//------------------
            # if texPROP["ParameterInfo"]["Name"] == "Diffuse":
            #     texImage.image.alpha_mode = 'CHANNEL_PACKED'
            #     byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])
            #     byoMAT.node_tree.links.new(bsdf.inputs['Alpha'], texImage.outputs['Alpha'])
            # elif texPROP["ParameterInfo"]["Name"] == "MRA":
            #     pass
            # elif texPROP["ParameterInfo"]["Name"] == "Normal":
            #     normalNode = byoMAT.node_tree.nodes.new('ShaderNodeNormalMap')
            #     byoMAT.node_tree.links.new(normalNode.inputs['Color'], texImage.outputs['Color'])
            #     byoMAT.node_tree.links.new(bsdf.inputs['Normal'], normalNode.outputs['Normal'])

            # elif texPROP["ParameterInfo"]["Name"] == "Diffuse A":

            #     mixNode = byoMAT.node_tree.nodes.new('ShaderNodeMixRGB')
            #     byoMAT.node_tree.links.new(mixNode.inputs['Color1'], texImage.outputs['Color'])
            # elif texPROP["ParameterInfo"]["Name"] == "Diffuse B":
            #     if mixNode:
            #         byoMAT.node_tree.links.new(mixNode.inputs['Color2'], texImage.outputs['Color'])
            #         byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], mixNode.outputs['Color'])
            # else:
            #     logger.info(texPROP["ParameterInfo"]["Name"])

    if "BasePropertyOverrides" in matJSON[0]["Properties"]:
        if "BlendMode" in matJSON[0]["Properties"]["BasePropertyOverrides"]:
            if matJSON[0]["Properties"]["BasePropertyOverrides"]["BlendMode"] == "BLEND_Translucent":
                Diffuse_Clip_Value = "CLIP"
                # byoMAT.blend_method = "CLIP"

        if "OpacityMaskClipValue" in matJSON[0]["Properties"]["BasePropertyOverrides"]:
            Diffuse_Alpha_Threshold = float(matJSON[0]["Properties"]["BasePropertyOverrides"]["OpacityMaskClipValue"])
            # byoMAT.alpha_threshold = float(matJSON[0]["Properties"]["BasePropertyOverrides"]["OpacityMaskClipValue"])

    if "VectorParameterValues" in matJSON[0]["Properties"]:
        for param in matJSON[0]["Properties"]["VectorParameterValues"]:
            if param["ParameterInfo"]["Name"] == "Layer A Tint":
                Layer_A_Tint = param["ParameterValue"]["Hex"]
            if param["ParameterInfo"]["Name"] == "Layer B Tint":
                Layer_B_Tint = param["ParameterValue"]["Hex"]
            if param["ParameterInfo"]["Name"] == "AO Color":
                AO_Color = param["ParameterValue"]["Hex"]

    if Blend_Power:
        mixNode = byoMAT.node_tree.nodes.new('ShaderNodeMixRGB')
        mixNode.inputs[0].default_value = Blend_Power
        byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], mixNode.outputs['Color'])

        if Diffuse_A_Map:
            byoMAT.node_tree.links.new(mixNode.inputs['Color1'], Diffuse_A_Map.outputs['Color'])
        if Diffuse_B_Map:
            byoMAT.node_tree.links.new(mixNode.inputs['Color2'], Diffuse_B_Map.outputs['Color'])
        if Diffuse_B_Low_Map:
            byoMAT.node_tree.links.new(mixNode.inputs['Color2'], Diffuse_B_Low_Map.outputs['Color'])
    if Diffuse_Map:
        byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], Diffuse_Map.outputs['Color'])

    # Arrange nodes so they look cool
    blenderUtils.arrangeNodes(byoMAT.node_tree)


def setMatsFromObject(byo: bpy.types.Object, objectJSON: dict, objectName: str):
    logger.info("Running : setMatsFromObject()")

    if "Properties" in objectJSON:
        if "StaticMaterials" in objectJSON["Properties"]:
            for i, mat in enumerate(objectJSON["Properties"]["StaticMaterials"]):
                yo = mat["MaterialInterface"]["ObjectPath"]
                matName = Path(os.path.splitext(yo)[0].strip("/")).name
                matPath = os.path.splitext(yo)[0].strip("/")
                matPathFull = CWD.joinpath("export", matPath).__str__() + ".json"

                # logger.info(f"yo : {matPathFull}")
                if "WorldGridMaterial" not in matPath:
                    if Path(matPathFull).exists():
                        logger.debug(f"Normal matJSON Found : {matPathFull}")
                        matJSON = readJSON(matPathFull)

                    try:
                        byoMAT = byo.material_slots[i].material
                        setMaterial(byoMAT, matJSON, objectName)
                    except IndexError:
                        pass

            else:
                pass


def setMaterialFromObject(byo: bpy.types.Object, matIndex: int, objectJSON: dict, objectName: str):
    logger.info("Running : setMaterialFromObject()")

    if "Properties" in objectJSON:
        if "StaticMaterials" in objectJSON["Properties"]:
            try:
                yo = objectJSON["Properties"]["StaticMaterials"][matIndex]["MaterialInterface"]["ObjectPath"]
                matName = Path(os.path.splitext(yo)[0].strip("/")).name
                matPath = os.path.splitext(yo)[0].strip("/")
                matPathFull = CWD.joinpath("export", matPath).__str__() + ".json"

                if "WorldGridMaterial" not in matPath:
                    if Path(matPathFull).exists():
                        matJSON = readJSON(matPathFull)
                        try:
                            byoMAT = byo.material_slots[matIndex].material
                            setMaterial(byoMAT, matJSON, objectName)
                        except IndexError:
                            pass
            except IndexError:
                pass


def objectSetMaterials(byo: bpy.types.Object, object):
    logger.info("Running : objectSetMaterials()")
    objectJSON = readJSON(getFixedPath(object) + ".json")
    objectJSON = objectJSON[2]
    objectName = objectJSON["Name"]

    # Check if it has an Overriden material
    if "OverrideMaterials" in object["Properties"]:
        pass
        # overrideMats = object["Properties"]["OverrideMaterials"]
        # for i, mat in enumerate(overrideMats):

        #     if mat is not None:

        #         matName = Path(os.path.splitext(mat["ObjectPath"])[0].strip("/")).name
        #         matPath = os.path.splitext(mat["ObjectPath"])[0].strip("/")
        #         matPathFull = CWD.joinpath("export", matPath).__str__() + ".json"
        #         if Path(matPathFull).exists():
        #             matJSON = readJSON(matPathFull)
        #             try:
        #                 byoMAT = byo.material_slots[i].material
        #                 setMaterial(byoMAT, matJSON, objectName)
        #             except IndexError:
        #                 pass

        #         else:
        #             logger.warning(f"matJSON Not Found : {matPathFull}")
        #     else:
        #         setMaterialFromObject(byo, i, objectJSON, objectName)

        # # If OverrideMaterial count doesn't match object's material count, use object's material data
        # if "Properties" in objectJSON:
        #     if "StaticMaterials" in objectJSON["Properties"]:
        #         if len(overrideMats) != len(objectJSON["Properties"]["StaticMaterials"]):
        #             setMatsFromObject(byo, objectJSON, objectName)

    # If not check the object path for a material file
    else:
        logger.info("OverrideMaterials not found in : {objectName}")
        setMatsFromObject(byo, objectJSON, objectName)


@timer
def main():

    CWD.joinpath("export", "Scenes").mkdir(parents=True, exist_ok=True)

    # Check if settings.ini file set up correctly.
    # If not break the loop
    if VAL_PATH == "":
        print("You didn't setup your 'settings.ini' file!")
        return False

    if checkExtracted(VAL_EXPORT_FOLDER):
        print("- JSONs are already extracted")
    else:
        print("JSONs are not found, starting exporting!")
        # Extract JSONs
        extractJSONs()

        # engineContent = CWD.joinpath("export", "Engine", "Content")
        # engineF = CWD.joinpath("export", "Engine")

        # for dir in engineContent.iterdir():
        #     for f in dir.iterdir():
        #         oPath = f.__str__()
        #         nPath = oPath.replace("Content", "").replace("\\\\", "\\")
        #         os.chdir(nPath)
        #         print(oPath, nPath)
        #         os.rename(oPath, nPath)

    # Check if everything is exported from uModel
    if checkExported(VAL_EXPORT_FOLDER):
        print("- Models are already extracted")
    else:
        print("Exports not found, starting exporting!")
        # Export Models
        exportAllModels()

    # # // --------------------------------------------------
    # # Blender Loop

    SELECTED_MAP = "bind"

    for i, umap in enumerate(_umapList.MAPS[SELECTED_MAP]):
        blenderUtils.cleanUP()
        umapName = os.path.splitext(os.path.basename(umap))[0]
        umapPath = CWD.joinpath("export", umap.replace(".umap", ".json"))
        umapDATA = readJSON(umapPath)

        # logger.info(umapName)
        print(umapName)

        # bpy.ops.scene.new(type="NEW")
        main_scene = bpy.data.scenes["Scene"]

        import_collection = bpy.data.collections.new(umapName)
        main_scene.collection.children.link(import_collection)

        print(f"Processing UMAP : {umapName}")

        for i, object in enumerate(umapDATA):

            if checkImportable(object):
                if i < 20000000:

                    # logger.debug(object["Properties"]["StaticMesh"]["ObjectPath"])
                    objName = getObjectname(object)
                    objPath = getFixedPath(object) + ".gltf"

                    if "GroundPaintedLines_0_BoxA" in objName:
                        if Path(objPath).exists():
                            # print("importing : ", objPath)
                            # logger.info(f"[{i}] : Importing GLTF : {objPath}")
                            print(f"[{i}] : Importing GLTF : {objPath}")
                            with redirect_stdout(stdout):
                                bpy.ops.import_scene.gltf(filepath=objPath, loglevel=5, merge_vertices=True)

                            imported = bpy.context.active_object

                            blenderUtils.objectSetProperties(imported, object)
                            objectSetMaterials(imported, object)

                            # Move Object to UMAP Collection
                            bpy.data.collections[umapName].objects.link(imported)
                            main_scene.collection.objects.unlink(imported)

                        else:
                            # print("Couldn't object's file : ", objPath)
                            logger.warning(f"Couldn't find Found GLTF : {objPath}")

        #  // ------------------------------------------
        #  // After this part saves the blend files, if working on the script, comment these out 
        #  // ------------------------------------------
        
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
    #         bpy.ops.wm.append(filepath=fp, filename=obj, directory=dr)
    # bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", SELECTED_MAP).__str__() + ".blend")


main()
