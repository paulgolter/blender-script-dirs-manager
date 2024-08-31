bl_info = {
    "name": "Project 2 Addon 1",
    "category": "Interface",
    "version": (0, 0, 1),
    "blender": (4, 00, 0),
    "description": "",
    "author": "",
}

import proj_02_utils
import proj_02_globals

def register():
    print("Project 2: Hello from Addon 1")

def unregister():
    print("Project 2: Bye from Addon 1")

