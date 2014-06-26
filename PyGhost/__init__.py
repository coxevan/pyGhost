import ghost_class as gc
import ghost_ui as gui

reload(gc)
reload(gui)


#PySide Window creation Error Check.
try:
    ui.deleteLater()

except:
    pass

ui = gui.PyGhostUi()

try:
    ui.create()
    ui.show()

except:
    ui.deleteLater()
    raise