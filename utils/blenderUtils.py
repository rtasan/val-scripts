import bpy
from math import radians
from collections import OrderedDict
from itertools import repeat


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

    # bpy.ops.scene.new(type='EMPTY')

def objectSetProperties(byo, object):
    try:
        byo.location = [
            object["RelativeLocation"]["X"] * 0.01,
            object["RelativeLocation"]["Y"] * -0.01,
            object["RelativeLocation"]["Z"] * 0.01
        ]
    except:
        pass
    try:
        byo.rotation_mode = 'XYZ'
        byo.rotation_euler = [
            radians(object["RelativeRotation"]["Roll"]),
            radians(-object["RelativeRotation"]["Pitch"]),
            radians(-object["RelativeRotation"]["Yaw"])
        ]
    except:
        pass
    try:
        byo.scale = [
            object["RelativeScale3D"]["X"],
            object["RelativeScale3D"]["Y"],
            object["RelativeScale3D"]["Z"],
        ]
    except:
        pass


def float_lerp(a, b, t):
    return (1.0 - t) * a + t * b
