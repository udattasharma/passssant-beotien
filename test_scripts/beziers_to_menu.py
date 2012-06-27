import bpy

sce = bpy.context.scene
#some variables
res = 3

#put your text file output here
file_path = "C://dev//buttons.txt"

txt = open(file_path, 'w')

#get the frame dimensions and aspect ratio
Frame = bpy.data.objects['Frame']

width = Frame.dimensions[0]
txt.write('width = ' + str(width) + '\n')

height = Frame.dimensions[1]
txt.write('height = ' + str(height) + '\n')

aspect = width/height
txt.write('aspect = ' + str(aspect) + '\n')

#get the scale that makes the x axis 1
#we will be applying it but it should be known
scale = 1/width
txt.write('scale = ' + str(scale) + '\n')

txt.write('button_data = [' + '\n')


bpy.ops.object.select_all(action = 'DESELECT')

#for each curve in the scene
for ob in bpy.data.objects:
    if ob.type == 'CURVE':
        txt.write('\n')
        
        #txt.write("#" + ob.name + '\n')
        #txt.write('loc = (' + str(scale * ob.location[0]) +  ',' + str(scale * ob.location[1])   + ')\n')
        
        
        
        #select it
        ob.select = True
        sce.objects.active = ob
    
        #set the u resolution
        ob.data.resolution_u = res
    
        #convert to mesh with all transforms applied
        #assume verts are ordered correctly :-/
        bpy.ops.object.convert(target='MESH',keep_original = True)
        mesh = bpy.context.object.data
        
        #apply rotation and scale and location
        bpy.ops.object.transform_apply(location = True, rotation=True, scale = True)
        
        #the new active object is the mesh
        mesh = bpy.context.object.data
        N =  len(mesh.vertices)
        
        #write the vertex data
        #txt.write('#Vertex Data' + '\n')
        txt.write('    [')

        for i in range(0,N-2):
            x = scale * mesh.vertices[i].co[0]
            y = scale * mesh.vertices[i].co[1]
            space = ''
            if i > 0:
                space = '    '
            txt.write(space + '(' + str(x) + ',' + str(y) + '),' + '\n')
        
        x = scale * mesh.vertices[N-1].co[0]
        y = scale * mesh.vertices[N-1].co[1]   
        txt.write('    (' + str(x) + ',' + str(y) + ')],' + '\n')
        
        #delete the object
        bpy.ops.object.delete()
        
txt.close()