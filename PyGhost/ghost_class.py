import pymel.core as py
import maya.mel as mel
import conditions as cond


class PyGhost():
    
    def __init__(self):
        """
        Instance creation.

        Creates condition checks
        Checks for existence of pyGhost_Node/pyGhost_NodeShape and pyGhost_Group
            If they don't exist, makes them.
        """
        self.create_conditions = [py.objExists("pyGhost_Node"),
                             py.objExists("pyGhost_Group"),
                             py.objExists("pyGhost_Position")]

        if cond.one_var_conditional(None, self.create_conditions):
            self.ghost_node = "pyGhost_Node"
            self.ghost_shape = "pyGhost_NodeShape"
            self.ghost_group = "pyGhost_Group"
            self.master_key_holder = "pyGhost_Position"
        else:
            self.ghost_node, self.ghost_shape = self.create_pfx_node()
            self.ghost_group = py.group(n="pyGhost_Group", em=True)
            self.master_key_holder = py.group(n="pyGhost_Position", em=True)

        self.ghosts_exist = self.create_child_list(self.ghost_group, True)
        self.holder_exist = self.create_child_list(self.master_key_holder, False)

        print "Ghosts already existing: {0}".format(self.ghosts_exist)
        print "Position holders already existing: {0}".format(self.holder_exist)

    def logic(self, **kwargs):
        """
        Calls all logic and definitions for creation of a single ghost object.

        Kwargs -
            name - name of character
            mesh - meshes to ghost

        Returns class instance with
        """
        selection = py.ls(sl=True)
        self.name = kwargs.setdefault('name')
        self.mesh = kwargs.setdefault('objects', selection)
        self.time = int(py.currentTime(q=True))

        if len(self.mesh) < 1:
            pass
        else:
            self.ghost_mesh, self.ghost_mesh_shape = self.duplicate_and_merge()
            self.ghosts_exist = self.create_child_list(self.ghost_group, True)
            self.connect_node_and_mesh()
            self.create_key_frame_node()
            self.holder_exist = self.create_child_list(self.master_key_holder, False)

            PyGhost.reference_layer(self.ghost_group, name="PyGhost_Layer")
            py.select(cl=True)

        return self

    def create_ghost_on_range(self, objects, name, **kwargs):
        playback_slider = mel.eval('$tmpVar=$gPlayBackSlider')
        range_start, range_end = py.timeControl(playback_slider, q=True, rangeArray=True)
        start = kwargs.setdefault('start', int(range_start))
        end = kwargs.setdefault('end', int(range_end))
        increment = kwargs.setdefault('increment', 2)

        for i in range(start, end, increment):
            print start
            print end
            py.currentTime(i)
            self.logic(objects=objects, name=name)
        py.currentTime(end)
        self.logic(objects=objects, name=name)

    def create_ghost_on_frame(self, objects, name, **kwargs):
        current_time = py.currentTime(q=True)
        time = kwargs.setdefault('time', current_time)
        py.currentTime(time)
        self.logic(objects=objects, name=name)
        py.currentTime(current_time)

# ---- Creation of Nodes ----

    def create_pfx_node(self):
        """
        Creates pfx node and sets attributes accordingly.

            overrideEnabled - 1
            overrideDisplayType - 2
            CreaseLines - 0
            borderLines - 0
            displayPercent - 100

        Returns py_ghost_node, py_ghost_shape_node
        """
        py_ghost_shape_node = py.createNode("pfxToon")
        py_ghost_node = py_ghost_shape_node.getParent()
        py.rename(py_ghost_node, "pyGhost_Node")
       
        PyGhost.lock_hide_transforms(py_ghost_node)
        
        py.setAttr("{0}.overrideEnabled".format(py_ghost_shape_node), 1)
        py.setAttr("{0}.overrideDisplayType".format(py_ghost_shape_node), 2)
        py.setAttr("{0}.creaseLines".format(py_ghost_shape_node), 0)
        py.setAttr("{0}.borderLines".format(py_ghost_shape_node), 0)
        py.setAttr("{0}.displayPercent".format(py_ghost_shape_node), 100)
        
        return py_ghost_node, py_ghost_shape_node
        
    def duplicate_and_merge(self):
        """
        Duplicates meshes and, locks and hide channelBox transform attributes
        Parents to ghost_group

        returns resulting ghost_mesh and ghost_mesh_shape
        """
        ghost_name = "{0}_{1}_{2}".format(self.name, self.time, "ghost")
        if py.objExists(ghost_name):
            py.delete(ghost_name)
        if len(self.mesh) > 1:
            temp_mesh = py.duplicate(self.mesh)
            ghost_mesh = py.polyUnite(temp_mesh, n=ghost_name)[0]
            py.delete(temp_mesh)
        else:
            ghost_mesh = py.duplicate(self.mesh, n=ghost_name)[0]
            ghost_mesh.hide()
        ghost_mesh_shape = ghost_mesh.getChildren()

        py.delete(ghost_mesh, ch=True)
        
        PyGhost.lock_hide_transforms(ghost_mesh)
        py.parent(ghost_mesh, self.ghost_group)
        
        return ghost_mesh, ghost_mesh_shape

    def create_key_frame_node(self):
        key_holder_name = "{0}_{1}".format(self.name, "keyholder")
        if not py.objExists(key_holder_name):
            key_holder = py.group(n=key_holder_name, em=True)
            py.parent(key_holder, self.master_key_holder)
        py.setKeyframe(key_holder_name, time=self.time)
        py.keyframe(key_holder_name, tds=True)
        PyGhost.lock_hide_transforms(key_holder_name)

        return key_holder_name

# ---- Connections & Utility -----

    def connect_node_and_mesh(self):
        """
        Connects ghost mesh with pfxGhostNode
        """
        count = len(self.ghosts_exist)
        i = 0
        while i < count:
            try:
                py.disconnectAttr("{0}.inputSurface[{1}].inputWorldMatrix".format(self.ghost_shape, i))
                py.disconnectAttr("{0}.inputSurface[{1}].surface".format(self.ghost_shape, i))

                py.connectAttr("{0}.outMesh".format(self.ghosts_exist[i][1]),
                               "{0}.inputSurface[{1}].surface".format(self.ghost_shape, i))
                py.connectAttr("{0}.worldMatrix[0]".format(self.ghosts_exist[i][1]),
                               "{0}.inputSurface[{1}].inputWorldMatrix".format(self.ghost_shape, i))
                i += 1
            except IndexError:
                break

    def delete(self, **kwargs):
        """
        Delete specified ghost(s)
            Either by name, all or by character

        Kwargs -
            byName - boolean *False
            currentTime - boolean *False
            name - name of character
        """
        time = int(py.currentTime(q=True))
        by_name = kwargs.setdefault('byName', False)
        current_time = kwargs.setdefault('currentTime', False)
        name = kwargs.setdefault('name', self.name)
        keyholder = "{0}_{1}".format(name, "keyholder")

        if current_time is True:
            current_time_name = "{0}_{1}_{2}".format(name, time, "ghost")
            try:
                py.delete(current_time_name)
                py.cutKey(keyholder, time=(time, time))
            except:
                py.warning("No ghost found on current frame!")
        elif by_name is True:
            py.delete(keyholder)
            for obj in self.ghosts_exist:
                if name == obj[0][:len(name)]:
                    print "Deleting {0}".format(obj)
                    py.delete(obj)
        else:
            for obj in self.ghosts_exist:
                try:
                    py.delete(obj)
                except:
                    raise
            for obj in self.holder_exist:
                try:
                    py.delete(obj)
                except:
                    raise
        self.ghosts_exist = self.create_child_list(self.ghost_group, True)
        self.holder_exist = self.create_child_list(self.master_key_holder, False)

    def create_child_list(self, m_obj, shape_bool):
        """
        Creates list of transforms and shapes for ghosts

        Returns list contents
        """
        transforms = py.listRelatives(m_obj, children=True)
        if shape_bool:
            shapes = [py.listRelatives(xform, children=True)[0] for xform in transforms]
            return [((transforms[i], shapes[i])) for i in xrange(0, len(transforms))]
        return [xform for xform in transforms]

    @classmethod
    def reference_layer(cls, objects, **kwargs):
        """
        Creates reference layer "Ref_Layer" if not already made or no new name is provided
        Adds object to new layer

        Returns new reference layer
        """
        layer = kwargs.setdefault('name', 'Ref_Layer')
        if py.objExists(layer) is False:
            py.createDisplayLayer(empty=True, n=layer)
            py.setAttr(layer+".dt", 2)
        py.editDisplayLayerMembers(layer, objects)

        return layer

    @classmethod
    def lock_hide_transforms(cls, node):
        attr_list = ["x", "y", "z"]
        for attr in attr_list:
            py.setAttr("{0}.t{1}".format(node, attr),
                       lock=True,
                       keyable=False,
                       channelBox=False)
            py.setAttr("{0}.r{1}".format(node, attr),
                       lock=True,
                       keyable=False,
                       channelBox=False)
            py.setAttr("{0}.s{1}".format(node, attr),
                       lock=True,
                       keyable=False,
                       channelBox=False)
