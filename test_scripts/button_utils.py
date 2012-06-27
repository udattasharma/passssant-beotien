import bpy
from mathutils import Vector
from mathutils.geometry import intersect_line_line_2d
from math import fmod

def outside_loop(loop):
    
    xs = [v[0] for v in loop]
    ys = [v[1] for v in loop]
    
    maxx = max(xs)
    maxy = max(ys)
    
    bound = (maxx +1 , maxy + 1)
    return bound

def point_inside_loop(loop, point):
    
    nverts = len(loop)
    
    #vectorize our two item tuple
    out = Vector(outside_loop(loop))
    pt = Vector(point)
    
    intersections = 0
    for i in range(0,nverts):
        a = Vector(loop[i-1])
        b = Vector(loop[i])
        if intersect_line_line_2d(pt,out,a,b):
            intersections += 1
    
    inside = False
    if fmod(intersections,2):
        inside = True
    
    return inside

#make sure this has all transformed applied
Circle = bpy.data.objects['Circle']
Cube = bpy.data.objects['Cube']

test_pt = (Cube.location[0],Cube.location[1])
test_loop = [(vert.co[0],vert.co[1]) for vert in Circle.data.vertices]

print(point_inside_loop(test_loop,test_pt))