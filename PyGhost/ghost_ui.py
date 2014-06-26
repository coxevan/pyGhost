from PyGhost import ghost_class as gc

from PySide import QtCore, QtGui

from shiboken import wrapInstance

import pymel.core as py
import maya.cmds as mc
import maya.OpenMayaUI as omui

reload(gc)


def maya_main_window():
    """
    Return the Maya main window widget as a Python object
    """
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtGui.QWidget)


class PyGhostUi(QtGui.QDialog):

    def __init__(self, parent=maya_main_window()):
        super(PyGhostUi, self).__init__(parent)
        self.name = "untitled"
        self.button_dict = {}
        self.line_edit_dict = {}
        self.list_selection = []
        ghost_instance = gc.PyGhost()
        self.static = ghost_instance.logic(objects=[])
        self.set_time = 1
        self.increment = 4

    def create(self):
        #Logic for creating window
        self.setWindowTitle("PyGhost")
        self.setWindowFlags(QtCore.Qt.Tool)
        self.setFixedSize(320, 460)

        self.create_widget()
        self.create_character_layout()
        self.create_connections()
        
    def create_widget(self):
        #Tuple = (dict_key, widget_label, tool_tip)
        button_key_list = [
            ("add_mesh", "Add Mesh", "Add mesh to list"),
            ("create_button", "At Current Frame", "Create a ghost of the current frame."),
            ("create_at_frame", "At Frame : ", "Create a ghost at frame number."),
            ("create_in_range", "In Selected Range :", "Create a ghost for each X in selected frames in time slider."),
            ("delete_all_ghost", "All Ghosts", "Delete all ghosts."),
            ("delete_frame_ghost", "Current Frame", "Delete all ghosts on current frame."),
            ("delete_char_ghost", "Current Character", "Delete only the current character's ghosts."),
            ("remove_all", "Remove All", "Remove all meshes from the list."),
            ("remove_selected", "Remove Selected", "Remove selected meshes from the list."),
            ("show_keys", "Show Ghost Time Positions", "Shows the position of ghosts in the time slider for current character")]

        line_edit_list = [
            ("char_name", "Name of Character", "Define or change the name of the current character."),
            ("at_frame", str(self.set_time), "Frame to create a ghost at."),
            ("increment", str(self.increment), "Every X frames in range, create a ghost")
        ]

        for button_tuple in button_key_list:
            self.button_dict[button_tuple[0]] = QtGui.QPushButton(button_tuple[1], whatsThis=button_tuple[2])

        for line_tuple in line_edit_list:
            self.line_edit_dict[line_tuple[0]] = QtGui.QLineEdit(line_tuple[1], whatsThis=line_tuple[2])

        self.create_label = QtGui.QLabel("Create Ghost :")
        self.delete_label = QtGui.QLabel("Delete :")

        self.line_slider = QtGui.QSlider(QtCore.Qt.Horizontal, maximum=200, minimum=0)
        self.current_space_label = QtGui.QLabel("Current Character : {0}".format(self.name))
        
        self.mesh_list = QtGui.QListWidget(sortingEnabled=True)
        self.mesh_list.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)

    def create_character_layout(self):
        self.remove_list_layout = QtGui.QHBoxLayout()
        self.remove_list_layout.addWidget(self.button_dict["remove_all"])
        self.remove_list_layout.addWidget(self.button_dict["remove_selected"])

        self.creation_layout = QtGui.QVBoxLayout()
        self.creation_layout.addWidget(self.line_edit_dict["char_name"])
        self.creation_layout.addWidget(self.button_dict["add_mesh"])
        self.creation_layout.addWidget(self.mesh_list)
        self.creation_layout.addLayout(self.remove_list_layout)

        self.creation_button_H_layout = QtGui.QHBoxLayout()
        self.creation_button_H_layout.addWidget(self.button_dict["create_at_frame"])
        self.creation_button_H_layout.addWidget(self.line_edit_dict["at_frame"])
        self.creation_button_H_layout.addWidget(self.button_dict["create_in_range"])
        self.creation_button_H_layout.addWidget(self.line_edit_dict["increment"])
        
        self.delete_layout = QtGui.QVBoxLayout()
        self.delete_layout.setSpacing(2)
        self.delete_layout.addWidget(self.delete_label)
        self.delete_layout.addWidget(self.button_dict["delete_all_ghost"])
        self.delete_layout.addWidget(self.button_dict["delete_frame_ghost"])
        self.delete_layout.addWidget(self.button_dict["delete_char_ghost"])

        self.main_layout = QtGui.QVBoxLayout()
        self.main_layout.addWidget(self.current_space_label)
        self.main_layout.addLayout(self.creation_layout)
        self.main_layout.addWidget(self.create_label)
        self.main_layout.addWidget(self.button_dict["create_button"])
        self.main_layout.addLayout(self.creation_button_H_layout)
        self.main_layout.addWidget(self.line_slider)
        self.main_layout.addWidget(self.button_dict["show_keys"])
        self.main_layout.addLayout(self.delete_layout)

        self.main_layout.addStretch()
        
        self.setLayout(self.main_layout)

    def create_connections(self):
        self.mesh_list.itemSelectionChanged.connect(self.on_select_changed)
        self.line_edit_dict["char_name"].textChanged.connect(self.on_text_edit)
        self.line_edit_dict["at_frame"].textChanged.connect(self.on_frame_edit)
        self.line_edit_dict["increment"].textChanged.connect(self.on_increment_edit)

        self.button_dict["create_button"].clicked.connect(self.py_ghost)
        self.button_dict["create_in_range"].clicked.connect(self.py_ghost_create_range)
        self.button_dict["create_at_frame"].clicked.connect(self.py_ghost_create_frame)
        self.button_dict["show_keys"].clicked.connect(self.select_key)

        self.button_dict["add_mesh"].clicked.connect(self.on_add_to_list)
        self.button_dict["remove_selected"].clicked.connect(self.on_delete_from_list)
        self.button_dict["remove_all"].clicked.connect(self.on_delete_from_list)

        self.button_dict["delete_frame_ghost"].clicked.connect(self.py_ghost_delete_time)
        self.button_dict["delete_char_ghost"].clicked.connect(self.py_ghost_delete_name)
        self.button_dict["delete_all_ghost"].clicked.connect(self.py_ghost_delete)

        self.line_slider.valueChanged.connect(self.on_slider_change)

    def list_creation(self):
        """
        Converts selection of QListObject into maya object name.
        Returns list of maya objects
        Returns False if AttributeError (nothing selected in list)
        """
        try:
            q_objects = self.list_selection
        except AttributeError:
            py.warning("Must have atleast 1 mesh selected in the mesh list!")
            return False
        m_objects = [obj.text() for obj in q_objects]
        return m_objects

    #SLOTS ---
    def on_select_changed(self):
        self.list_selection = self.mesh_list.selectedItems()

    def on_increment_edit(self):
        self.increment = int(self.sender().text())

    def on_frame_edit(self):
        sender = self.sender()
        self.set_time = int(sender.text())

    def on_text_edit(self):
        sender = self.sender()
        self.name = str(sender.text())
        self.current_space_label.setText("Current Character : {0}".format(self.name))
        
    def on_add_to_list(self):
        sender = self.sender()
        if sender.text() == "Add Mesh":
            selection = []
            raw_selection = mc.ls(dag=True, g=True, ap=True, sl=True, st=True)
            shape_selection = [raw_selection[i] for i in xrange(0, len(raw_selection), 2) if raw_selection[i+1] == "mesh"]
            transform_selection = [mc.listRelatives(shape, parent=True)[0] for shape in shape_selection]
            for transform in transform_selection:
                search_result = self.mesh_list.findItems(transform, QtCore.Qt.MatchFixedString)
                if len(search_result) > 0:
                    pass
                else:
                    print len(search_result)
                    selection.append(transform)
            self.mesh_list.addItems(selection)
            #for select in selection:
            #print self.mesh_list.findItems(select, QtCore.Qt.MatchFixedString)

    def on_delete_from_list(self):
        sender = self.sender()
        if sender.text() == "Remove Selected":
            selected = self.mesh_list.selectedItems()
            for list_object in selected:
                row = self.mesh_list.row(list_object)
                self.mesh_list.takeItem(row)
        else:
            print self.mesh_list.count()
            for i in xrange(0, self.mesh_list.count()):
                self.mesh_list.takeItem(0)

    def on_slider_change(self):
        sender = self.sender()
        raw_value = sender.value()
        value = raw_value * 0.01
        py.setAttr("pyGhost_Node.lineWidth", value)

    def select_key(self):
        py.select("{0}_{1}".format(self.name, "keyholder"))

    #SLOT METHODS ---
    def py_ghost(self):
        m_objects = self.list_creation()
        if m_objects is False:
            pass
        else:
            self.current_space_label.setText("Current Character : {0}".format(self.name))
            self.static.logic(objects=m_objects, name=self.name)

    def py_ghost_create_frame(self):
        m_objects = self.list_creation()
        self.static.create_ghost_on_frame(m_objects, self.name, time=self.set_time)

    def py_ghost_create_range(self):
        m_objects = self.list_creation()
        self.static.create_ghost_on_range(m_objects, self.name, increment=self.increment)

    def py_ghost_delete(self):
        self.static.delete()

    def py_ghost_delete_time(self):
        self.static.delete(currentTime=True)

    def py_ghost_delete_name(self):
        self.static.delete(byName=True, name=self.name)