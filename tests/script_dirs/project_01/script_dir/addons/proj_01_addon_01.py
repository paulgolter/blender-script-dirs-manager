bl_info = {
    "name": "Project 1 Addon 1",
    "category": "Interface",
    "version": (0, 0, 1),
    "blender": (4, 00, 0),
    "description": "",
    "author": "",
}

import proj_01_utils

def register():
    print("Project 1: Hello from Addon 1")

def unregister():
    print("Project 1: Bye from Addon 1")





