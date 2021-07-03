import io
import subprocess
import os
import json
import logging
import sys
from typing import Text
import bpy
import importlib
from time import time
from contextlib import redirect_stdout
from math import radians
from mathutils import Vector
from pathlib import Path
from configparser import BasicInterpolation, ConfigParser
from collections import OrderedDict
from itertools import repeat


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
logger.addHandler(fh)
logger.addHandler(ch)


try:
    sys.path.append(CWD.__str__())
    from utils import _umapList
    importlib.reload(_umapList)

except:
    print("An exception occurred")


def float_lerp(a, b, t):
    return (1.0 - t) * a + t * b


def calc_priority_by_socket(node):
    if len(node.inputs) is 0:
        return -9999
    if len(node.outputs) is 0:
        return 9999

    result = 0
    for in_socket in node.inputs:
        if in_socket.is_linked:
            for link in in_socket.links:
                if link.is_valid:
                    if len(link.from_node.inputs) is 0:
                        result -= 1
                    else:
                        result += 2

    for out_socket in node.outputs:
        if out_socket.is_linked:
            for link in out_socket.links:
                if link.is_valid:
                    if len(link.to_node.outputs) is 0:
                        result += 10
                    else:
                        result -= 1

    return result


def calc_priority_by_type(node):
    if node.type == 'NEW_GEOMETRY' or node.type == 'TEX_COORD' or node.type == 'GROUP_INPUT':
        return -6
    if node.type == 'VALUE' or node.type == 'ATTRIBUTE':
        return -5
    if node.type == 'SEPXYZ':
        return -4
    if node.type == 'SEPHSV' or node.type == 'SEPRGB' or node.type == 'BLACKBODY':
        return -3
    if node.type == 'MATH' or node.type == 'VECT_MATH':
        return -2
    if node.type == 'COMBXYZ':
        return -1
    if node.type == 'COMBHSV' or node.type == 'COMBRGB':
        return 1
    if node.type == 'MIX_RGB' or node.type == 'HUE_SAT':
        return 2
    if node.type == 'TEX_IMAGE' or node.type == 'TEX_MUSGRAVE' or node.type == 'TEX_BRICK' or node.type == 'TEX_NOISE' or node.type == 'TEX_VORONOI':
        return 3
    if node.type == 'BSDF_DIFFUSE' or node.type == 'BSDF_PRINCIPLED' or node.type == 'EMISSION':
        return 4
    if node.type == 'HOLDOUT' or node.type == 'VOLUME_SCATTER' or node.type == 'VOLUME_ABSORPTION':
        return 5
    if node.type == 'MIX_SHADER':
        return 6
    if node.type == 'OUTPUT_MATERIAL' or node.type == 'OUTPUT_LAMP' or node.type == 'GROUP_OUTPUT':
        return 7

    return 0


def arrangeNodes_A(node_array, calc_priority, horiz_padding=0.125, vert_padding=0.125):
    def sum_heights(nodes_array):
        result = 0
        for node in nodes_array:
            result = result + node.height
        return result

    def sum_widths(depth_nodes):
        result = 0
        for depth in depth_nodes:
            max_width = 0
            for node in depth_nodes[depth]:
                if max_width < node.width:
                    max_width = node.width
            result = result + max_width
        return result

    # Create a dictionary where the key is the
    # depth and the value is an array of nodes.
    depth_nodes = {}
    for node in node_array:

        depth = calc_priority(node)
        if depth in depth_nodes:

            # Add the node to the node array at that depth.
            depth_nodes[depth].append(node)
        else:

            # Begin a new array.
            depth_nodes[depth] = [node]

    # Add padding to half the width.
    extents_w = (0.5 + horiz_padding) * sum_widths(depth_nodes)
    t_w_max = 0.5
    sz0 = len(depth_nodes)
    if sz0 > 1:
        t_w_max = 1.0 / (sz0 - 1)

    # List of dictionary KVPs.
    depths = sorted(depth_nodes.items())
    depths_range = range(0, sz0, 1)
    for i in depths_range:
        nodes_array = depths[i][1]
        t_w = i * t_w_max
        x = float_lerp(-extents_w, extents_w, t_w)

        extents_h = (0.5 + vert_padding) * sum_heights(nodes_array)
        t_h_max = 0.5
        sz1 = len(nodes_array)
        if sz1 > 1:
            t_h_max = 1.0 / (sz1 - 1)

        nodes_range = range(0, sz1, 1)
        for j in nodes_range:
            node = nodes_array[j]
            t_h = j * t_h_max
            y = float_lerp(-extents_h, extents_h, t_h)
            half_w = 0.5 * node.width
            half_h = 0.5 * node.height
            node.location.xy = (x - half_w, y - half_h)


def arrangeNodes(nodeTree):
    # print(nodeTree)

    class values():
        average_y = 0
        x_last = 0
        margin_x = 300
        mat_name = ""
        margin_y = 150

    def nodes_arrange(nodelist, level):
        parents = []
        for node in nodelist:
            parents.append(node.parent)
            node.parent = None
            node.update()

        widthmax = max([x.dimensions.x for x in nodelist])
        xpos = values.x_last - (widthmax + values.margin_x) if level != 0 else 0
        values.x_last = xpos

        # node y positions
        x = 0
        y = 0

        for node in nodelist:

            if node.hide:
                hidey = (node.dimensions.y / 2) - 8
                y = y - hidey
            else:
                hidey = 0

            node.location.y = y
            y = y - values.margin_y - node.dimensions.y + hidey

            node.location.x = xpos  # if node.type != "FRAME" else xpos + 1200

        y = y + values.margin_y

        center = (0 + y) / 2
        values.average_y = center - values.average_y

        # for node in nodelist:

        #node.location.y -= values.average_y

        for i, node in enumerate(nodelist):
            node.parent = parents[i]

    def nodes_odd(ntree, nodelist):

        nodes = ntree.nodes
        for i in nodes:
            i.select = False

        a = [x for x in nodes if x not in nodelist]
        # print ("odd nodes:",a)
        for i in a:
            i.select = True

    def outputnode_search(ntree):    # return node/None
        outputnodes = []
        for node in ntree.nodes:
            if not node.outputs:
                for input in node.inputs:
                    if input.is_linked:
                        outputnodes.append(node)
                        break

        if not outputnodes:
            print("No output node found")
            return None
        return outputnodes

    def nodes_iterate(ntree, arrange=True):
        nodeoutput = outputnode_search(ntree)
        if nodeoutput is None:
            #print ("nodeoutput is None")
            return None
        a = []
        a.append([])
        for i in nodeoutput:
            a[0].append(i)

        level = 0

        while a[level]:
            a.append([])

            for node in a[level]:
                inputlist = [i for i in node.inputs if i.is_linked]

                if inputlist:

                    for input in inputlist:
                        for nlinks in input.links:
                            node1 = nlinks.from_node
                            a[level + 1].append(node1)

                else:
                    pass

            level += 1

        del a[level]
        level -= 1

        # remove duplicate nodes at the same level, first wins
        for x, nodes in enumerate(a):
            a[x] = list(OrderedDict(zip(a[x], repeat(None))))

        # remove duplicate nodes in all levels, last wins
        top = level
        for row1 in range(top, 1, -1):
            for col1 in a[row1]:
                for row2 in range(row1-1, 0, -1):
                    for col2 in a[row2]:
                        if col1 == col2:
                            a[row2].remove(col2)
                            break

        if not arrange:
            nodelist = [j for i in a for j in i]
            nodes_odd(ntree, nodelist=nodelist)
            return None

        ########################################

        levelmax = level + 1
        level = 0
        values.x_last = 0

        while level < levelmax:

            values.average_y = 0
            nodes = [x for x in a[level]]
            #print ("level, nodes:", level, nodes)
            nodes_arrange(nodes, level)

            level = level + 1

        return None

    def nodes_center(ntree):

        bboxminx = []
        bboxmaxx = []
        bboxmaxy = []
        bboxminy = []

        for node in ntree.nodes:
            if not node.parent:
                bboxminx.append(node.location.x)
                bboxmaxx.append(node.location.x + node.dimensions.x)
                bboxmaxy.append(node.location.y)
                bboxminy.append(node.location.y - node.dimensions.y)

        # print ("bboxminy:",bboxminy)
        bboxminx = min(bboxminx)
        bboxmaxx = max(bboxmaxx)
        bboxminy = min(bboxminy)
        bboxmaxy = max(bboxmaxy)
        center_x = (bboxminx + bboxmaxx) / 2
        center_y = (bboxminy + bboxmaxy) / 2

        x = 0
        y = 0

        for node in ntree.nodes:

            if not node.parent:
                node.location.x -= center_x
                node.location.y += -center_y

    def nodemargin(ntree):

        # values.margin_x = context.scene.nodemargin_x
        # values.margin_y = context.scene.nodemargin_y

        # ntree = context.space_data.node_tree
        # ntree = context

        # first arrange nodegroups
        # n_groups = []
        # for i in ntree.nodes:
        #     if i.type == 'GROUP':
        #         n_groups.append(i)

        # while n_groups:
        #     j = n_groups.pop(0)
        #     nodes_iterate(j.node_tree)
        #     for i in j.node_tree.nodes:
        #         if i.type == 'GROUP':
        #             n_groups.append(i)

        nodes_iterate(ntree)

        # arrange nodes + this center nodes together
        # if context.scene.node_center:
        nodes_center(ntree)

    nodemargin(nodeTree)


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


def readJSON(f: str):
    # 'C:\\Users\\ogulc\\Desktop\\valorant\\valpy\\export\\Engine\\BasicShapes\\Plane.json'
    # 'C:\\Users\\ogulc\\Desktop\\valorant\\valpy\\export\\Engine\\Content\\BasicShapes\\Plane.json'

    if "\\Engine" in f.__str__():
        f = f.__str__().replace("\Engine", "\\Engine\\Content")

    with open(f, 'r') as jsonFile:
        data = jsonFile.read()
        return json.loads(data)


def cleanUP():
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)

    for block in bpy.data.materials:
        bpy.data.materials.remove(block)

    for block in bpy.data.textures:
        bpy.data.textures.remove(block)

    for block in bpy.data.images:
        bpy.data.images.remove(block)

    for block in bpy.data.collections:
        bpy.data.collections.remove(block)

    for block in bpy.data.objects:
        bpy.data.objects.remove(block)


def importObject(object):
    pass


def checkImportable(object):
    if object["Type"] == "StaticMeshComponent" or object["Type"] == "InstancedStaticMeshComponent":
        if "StaticMesh" in object["Properties"]:
            return True


def writeToJson(f, d):
    with open(os.path.join(CWD.__str__(), "errors", f"{f}.json"), 'w') as outfile:
        json.dump(d, outfile, indent=4)


def objectSetProperties(byo, object):
    try:
        byo.location = [
            object["Properties"]["RelativeLocation"]["X"] * 0.01,
            object["Properties"]["RelativeLocation"]["Y"] * -0.01,
            object["Properties"]["RelativeLocation"]["Z"] * 0.01
        ]
    except:
        pass
        # logger.warning(f"{byo.name} doesn't have the Scale key!")
    try:
        byo.rotation_mode = 'XYZ'
        byo.rotation_euler = [
            radians(object["Properties"]["RelativeRotation"]["Roll"]),
            radians(-object["Properties"]["RelativeRotation"]["Pitch"]),
            radians(-object["Properties"]["RelativeRotation"]["Yaw"])
        ]
    except:
        pass
        # logger.warning(f"{byo.name} doesn't have the Scale key!")
    try:
        byo.scale = [
            object["Properties"]["RelativeScale3D"]["X"],
            object["Properties"]["RelativeScale3D"]["Y"],
            object["Properties"]["RelativeScale3D"]["Z"],
        ]
    except:
        pass
        # logger.warning(f"{byo.name} doesn't have the Scale key!")


def getFixedPath(object):
    return CWD.joinpath("export", os.path.splitext(object["Properties"]["StaticMesh"]["ObjectPath"])[0].strip("/")).__str__()


def getObjectname(object):
    return Path(object["Properties"]["StaticMesh"]["ObjectPath"]).stem


# def setMatProperty(byoMAT: bpy.types.Material, dict):
#     pass

def setMaterial(byoMAT: bpy.types.Material, matJSON: dict, objectName: str):
    byoMAT.node_tree.nodes.new('ShaderNodeGroup')

    byoMAT.use_nodes = True
    byoMAT.name = matJSON[0]["Name"]
    byoTREE = byoMAT.node_tree
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
    # DFAPath = ""
    # DFBPath = ""
    # NMAPath = ""
    # NMBPath = ""
    # TRGBPath = ""
    # DFPath = ""
    # MRAPath = ""
    # MRAAPath = ""
    # MRABPath = ""
    # NMPath = ""
    # MRSPath = ""
    # AEMPath = ""

    # DFAlpha = False
    # DFClipValue = ""
    # DFAlphaEmi = False
    # DFEmi = True

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
    elif Diffuse_Map:
        byoMAT.node_tree.links.new(bsdf.inputs['Base Color'], Diffuse_Map.outputs['Color'])

    # if

    # node_arrange.NA_OT_NodeButton.execute()
    # arrangeNodes(byoMAT.node_tree.nodes, calc_priority_by_type)
    arrangeNodes(byoMAT.node_tree)
    # byoMAT.node_tree.update()


def setMatsFromObject(byo: bpy.types.Object, objectJSON: dict, objectName: str):
    # logger.info(f"Called setMatBack : {byo} - {matIndex} - {objectJSON}")
    if "Properties" in objectJSON:
        # logger.info(f"Found Properties in : {objectName}")
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
                # writeToJson(f=byo.name, d=objectJSON)
    # for i in range(0, 10):
        # byoMAT.node_tree.nodes[0]


def setMatBack(byo: bpy.types.Object, matIndex: int, objectJSON: dict, objectName: str):
    # matPath = os.path.splitext(mat["MaterialInterface"]["ObjectPath"])[0].strip("/")

    # logger.info(f"Called setMatBack : {byo} - {matIndex} - {objectJSON}")
    if "Properties" in objectJSON:
        # logger.info(f"Found Properties in : {objectJSON}")
        if "StaticMaterials" in objectJSON["Properties"]:
            try:
                yo = objectJSON["Properties"]["StaticMaterials"][matIndex]["MaterialInterface"]["ObjectPath"]
                matName = Path(os.path.splitext(yo)[0].strip("/")).name
                matPath = os.path.splitext(yo)[0].strip("/")
                matPathFull = CWD.joinpath("export", matPath).__str__() + ".json"

                if "WorldGridMaterial" not in matPath:
                    if Path(matPathFull).exists():
                        # logger.debug(f"Normal matJSON Found : {matPathFull}")
                        matJSON = readJSON(matPathFull)
                        try:
                            byoMAT = byo.material_slots[matIndex].material
                            setMaterial(byoMAT, matJSON, objectName)
                        except IndexError:
                            pass
                            # logger.warning(F"WHAT THE FUCK : {objectJSON}")
            except IndexError:
                pass


def objectSetMaterials(byo: bpy.types.Object, object):
    objectJSON = readJSON(getFixedPath(object) + ".json")
    objectJSON = objectJSON[2]
    objectName = objectJSON["Name"]

    if "OverrideMaterials" in object["Properties"]:
        overrideMats = object["Properties"]["OverrideMaterials"]
        for i, mat in enumerate(overrideMats):

            if mat is not None:

                matName = Path(os.path.splitext(mat["ObjectPath"])[0].strip("/")).name
                matPath = os.path.splitext(mat["ObjectPath"])[0].strip("/")
                matPathFull = CWD.joinpath("export", matPath).__str__() + ".json"
                # logger.warning(f"Setting using : {matPathFull} ")

                if Path(matPathFull).exists():
                    # logger.debug(f"Override matJSON Found : {matPathFull}")

                    matJSON = readJSON(matPathFull)

                    try:
                        byoMAT = byo.material_slots[i].material
                        setMaterial(byoMAT, matJSON, objectName)
                    except IndexError:
                        pass

                else:
                    logger.warning(f"matJSON Not Found : {matPathFull}")
            else:
                # logger.debug(f"Material is : {mat}, use MI.json from the object path")
                setMatBack(byo, i, objectJSON, objectName)

        if "Properties" in objectJSON:
            # logger.info(f"Found Properties in : {objectName}")
            if "StaticMaterials" in objectJSON["Properties"]:
                if len(overrideMats) != len(objectJSON["Properties"]["StaticMaterials"]):
                    setMatsFromObject(byo, objectJSON, objectName)

    else:
        # logger.info("OverrideMaterials not found in : {objectName}")
        setMatsFromObject(byo, objectJSON, objectName)


@timer
def main():

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
        cleanUP()
        umapName = os.path.splitext(os.path.basename(umap))[0]
        umapPath = CWD.joinpath("export", umap.replace(".umap", ".json"))
        umapDATA = readJSON(umapPath)

        logger.info(umapName)

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

                    if "Floor_12_ABombsiteB_1CollisionPrim" in objPath:
                        if Path(objPath).exists():
                            # print("importing : ", objPath)
                            logger.info(f"[{i}] : Importing GLTF : {objPath}")
                            with redirect_stdout(stdout):
                                bpy.ops.import_scene.gltf(filepath=objPath, loglevel=5, merge_vertices=True)

                            imported = bpy.context.active_object

                            objectSetProperties(imported, object)
                            objectSetMaterials(imported, object)

                            # Move Object to UMAP Collection
                            bpy.data.collections[umapName].objects.link(imported)
                            main_scene.collection.objects.unlink(imported)

                        else:
                            # print("Couldn't object's file : ", objPath)
                            logger.warning(f"Couldn't find Found GLTF : {objPath}")

    #     # Save to .blend file
        # bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", umapName).__str__() + ".blend")

    # cleanUP()
    # bpy.ops.wm.save_as_mainfile(filepath=CWD.joinpath("export", "Scenes", SELECTED_MAP).__str__() + ".blend")
    # # CWD.joinpath("export", "Scenes", umapName).__str__() + ".blend"
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


