bl_info = {
    "name": "Project 2 Addon 2",
    "category": "Interface",
    "version": (0, 0, 1),
    "blender": (4, 00, 0),
    "description": "",
    "author": "",
}

import proj_02_utils

def register():
    print("Project 2: Hello from Addon 2")

def unregister():
    print("Project 2: Bye from Addon 2")





