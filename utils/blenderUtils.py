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


# def objectSetPropertiesJSON(byo, object):
#     try:
#         byo.location = [
#             object["Properties"]["RelativeLocation"]["X"] * 0.01,
#             object["Properties"]["RelativeLocation"]["Y"] * -0.01,
#             object["Properties"]["RelativeLocation"]["Z"] * 0.01
#         ]
#     except:
#         pass
#     try:
#         byo.rotation_mode = 'XYZ'
#         byo.rotation_euler = [
#             radians(object["Properties"]["RelativeRotation"]["Roll"]),
#             radians(-object["Properties"]["RelativeRotation"]["Pitch"]),
#             radians(-object["Properties"]["RelativeRotation"]["Yaw"])
#         ]
#     except:
#         pass
#     try:
#         byo.scale = [
#             object["Properties"]["RelativeScale3D"]["X"],
#             object["Properties"]["RelativeScale3D"]["Y"],
#             object["Properties"]["RelativeScale3D"]["Z"],
#         ]
#     except:
#         pass


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
