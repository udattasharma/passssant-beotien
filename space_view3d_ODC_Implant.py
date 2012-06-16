# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    'name': "Implant Planer",
    'author': "Patrick Moore",
    'version': (0,0,1),
    'blender': (2, 5, 9),
    'api': 39307,
    'location': "3D View -> Tool Shelf",
    'description': "Tools to Help with Implant Planning",
    'warning': "",
    'wiki_url': "",
    'tracker_url': "",
    'category': '3D View'}


import bpy
from math import *
from mathutils import *
from mathutils import Vector
import time
import os
from bpy_extras.io_utils import ExportHelper, ImportHelper
from bpy.props import StringProperty, BoolProperty, CollectionProperty


## Changes in Rev. 0.0.1 9/17/2011
    #- Started layout of code

## Changes in Rev. 0.0.1 9/17/2011
    #- Added update function for custom properties
    #- Initiated funciton arguments and layout
    
## Changes in Rev. 0.0.1 9/26/2011
    #- Changed the name of some of the properties for code readability
    #  This will make old .blend files not work.
    #- Trying to plan integration with the fixed module.
    
## Changes in Rev. 0.0.1 9/27/2011
    #- Changed some of the materials and how they are assigned to match
    #  manufacturer's conventions
    #- In integrating with the fixed module, work on assignment of different
    #  objects to different layers to improve visibility instead of different
    #  scenes as per Thierie's method.

        #A note on layers organization
        #Layer 0 will be our master layer, everything is in it.
        #if we are just doing restorative or just implant planning
        #there is no need to utilize the other layers
        
        #1. All fixed items  (models, preps, margins)
        #2. All Implant objects (bone, implants, hardware etc)
        #3. Just Bone
        #4. Just Intraoral Scans
        #5. Just Preps
        #6. Just Implants with Abutments (no other hardware)
        #7. just Restorations   
        
        
          
##########################################
######  Useful Functions  ################
##########################################
################################################################################

from addon_utils import check,paths,enable
def get_all_addons(display=False):
    """
    Prints the addon state based on the user preferences.
    """
    import sys


    # RELEASE SCRIPTS: official scripts distributed in Blender releases
    paths_list = paths()
    addon_list = []
    for path in paths_list:
        bpy.utils._sys_path_ensure(path)
        for mod_name, mod_path in bpy.path.module_names(path):
            is_enabled, is_loaded = check(mod_name)
            addon_list.append(mod_name)
            if display:  #for example
                print("%s default:%s loaded:%s"%(mod_name,is_enabled,is_loaded))
            
    return(addon_list)

#print all the addons and show if enabled and default

addons = get_all_addons(True)


#enable dependencies

addon_dependencies = ['mesh_looptools','mesh_bsurfaces','mesh_relax']
for addon in addon_dependencies:
    if addon in addons:
        is_enabled, is_loaded = check(addon)
        if not is_enabled:
            enable(addon)
    else:
        print("Error Dependency %s missing"%addon)

#make a funtion to delete mesh data
def removeMeshFromMemory (passedName):
    try:
        me = bpy.data.meshes[passedName]
    except:
        me = None
    if me != None:
        me.user_clear()
        bpy.data.meshes.remove(me) 
    return

#make an update function which is stupid
def update_func(self, context):
    
    print("update my test function", self)
    sce = bpy.context.scene
    
    #gather all the relevant active and selected things
    ob_now = bpy.context.object
    if ob_now:
        mode_now = bpy.context.object.mode
    else:
        mode_now = bpy.context.mode        
    sel_now = bpy.context.selected_objects
    
    #Add a dummy plane to toggle editmode with
    if mode_now != 'OBJECT':
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
    bpy.ops.object.select_all(action = 'DESELECT')
    bpy.ops.mesh.primitive_plane_add()
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.object.mode_set()
    
    #prepare to delete our dummy plane
    plane = bpy.context.object
    data = plane.data.name    
    bpy.ops.object.delete()
    removeMeshFromMemory(data)
    
    #put the scene back like we found it
    bpy.ops.object.select_all(action = 'DESELECT')
    if ob_now:
        sce.objects.active = ob_now
        ob_now.select = True
    for ob in sel_now:
        ob.select = True        
    bpy.ops.object.mode_set(mode = mode_now)

##########################################
####### Custom Properties ################
##########################################

class WorkingSpace(bpy.types.PropertyGroup):
    
    name = bpy.props.StringProperty(name="Tooth Number",default="")
    implant = bpy.props.StringProperty(name="Implant Model",default="")
    outer = bpy.props.StringProperty(name="Outer Cylinder",default="")
    inner = bpy.props.StringProperty(name="Inner Cylinder",default="")
    cutout = bpy.props.StringProperty(name="Cutout Cylinder",default="")
    #mesial = bpy.props.StringProperty(name="Distal Model",default="")
    #distal = bpy.props.StringProperty(name="Distal Model",default="")
    #prep_model = bpy.props.StringProperty(name="Prep Model",default="")
    #margin = bpy.props.StringProperty(name="Margin",default="")
    #bubble = bpy.props.StringProperty(name="Bubble",default="")
    #restoration = bpy.props.StringProperty(name="Restoration",default="")
    #contour = bpy.props.StringProperty(name="Full Contour",default="")
    #coping = bpy.props.StringProperty(name="Simple Coping",default="")
    #acoping = bpy.props.StringProperty(name="Anatomic Coping",default="")
    #inside = bpy.props.StringProperty(name="Inside",default="")
    #in_bridge = bpy.props.BoolProperty(name="Incude in Bridge", default=False)
    
    #rest_types=['CONTOUR',
                #'PONTIC',
                #'COPING',
                #'ANATOMIC COPING']
    #rest_enum = []
    #for index, type in enumerate(rest_types):
        #rest_enum.append((str(index), rest_types[index], str(index)))
        
    #rest_type = bpy.props.EnumProperty(
        #name="Restoration Type", 
        #description="The type of restoration for this tooth", 
        #items=rest_enum, 
        #default='0',
        #options={'ANIMATABLE'})

    
bpy.utils.register_class(WorkingSpace)

bpy.types.Scene.working_space = bpy.props.CollectionProperty(type=WorkingSpace)
bpy.types.Scene.working_space_index = bpy.props.IntProperty(min=0, default=0, update=update_func)

class Splints(bpy.types.PropertyGroup):
    

    name = bpy.props.StringProperty(name="Patient Name",default="")
    
    
    plane = bpy.props.StringProperty(name="Occlusal Plane",default="")
    axis = bpy.props.StringProperty(name="Insertion Axis",default="")
    splint = bpy.props.StringProperty(name="Splint Model",default="")
    #cusps = bpy.props.StringProperty(name="Cusp Line",default="")
    #surface = bpy.props.StringProperty(name="Cusp Surface",default="")
    #outline = bpy.props.StringProperty(name="Outline",default="")
    
    
bpy.utils.register_class(Splints)

bpy.types.Scene.splint = bpy.props.CollectionProperty(type=Splints)
bpy.types.Scene.splint_index = bpy.props.IntProperty(min=0, default=0)


class LibraryImplant(bpy.types.PropertyGroup):
    
    name = bpy.props.StringProperty(name="Implant Name",default="")
    filepath = bpy.props.StringProperty(
            name="Folder",
            default="",
            subtype='DIR_PATH')
    hardware = bpy.props.BoolProperty(name = "hardware", default = False)
            
    ### Add other properties? like length, succes rate?, anerior/posterior"
    ### Brand etc.


    
bpy.utils.register_class(LibraryImplant)

bpy.types.Scene.library_implants = bpy.props.CollectionProperty(type=LibraryImplant)
bpy.types.Scene.library_implants_index = bpy.props.IntProperty(min=0, default=0, update=update_func)




##########################################
#######      Operators    ################
##########################################

################################################################################
class AppendSplint(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.append_splint'
    bl_label = "Append Splint"
    bl_options = {'REGISTER','UNDO'}
    
    name = bpy.props.StringProperty(name="Patient Name",default="")  
    
    def invoke(self, context, event): 
        
        
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
    
    def execute(self, context):

        my_item = bpy.context.scene.splint.add()        
        my_item.name = self.name
        
        return {'FINISHED'}

class RemoveSplint(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.remove_splint'
    bl_label = "Remove Splint"
       
    def execute(self, context):

        j = bpy.context.scene.splint_index
        bpy.context.scene.splint.remove(j)
        
        
        return {'FINISHED'}

class DefineSplintAxis(bpy.types.Operator):

    ''''''
    bl_idname = 'view3d.define_splint_axis'
    bl_label = "Define Splint Axis"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):

        sce = bpy.context.scene        
        master=sce.master_model        
        
        
        j = sce.splint_index
        splint = sce.splint[j]
        
        axis = splint.axis
        
       
        #check to make sure the master model is set
        if not master:
            self.report({'WARNING'}, "There is no master model.  Please define one first")
            return{'CANCELLED'}
        
        Master=sce.objects[master]
            
        #Delete the old one if it's there
        if axis:
            Empty = sce.objects[axis]
            #manually deselect since hidden things wont get deselected...thereby deleting them :/
            for ob in sce.objects:
                ob.select = False
            Empty.hide = False
            Empty.select = True
            sce.objects.active = Empty
            sce.objects.unlink(Empty)
            bpy.data.objects.remove(Empty)
            splint.axis = ''
            
        
        #Add a new one
        current_objects=list(bpy.data.objects)
        bpy.ops.object.add(type = 'EMPTY')
        for o in bpy.data.objects:
            if o not in current_objects:
                Empty = o
                o.name = 'Splint Axis'
                splint.axis = o.name

        #Get the view direction
        space = bpy.context.space_data
        region = space.region_3d        
        vrot = region.view_rotation       
        align = vrot.inverted()
        
        #Rotate the master model so that the current view
        #corresponds to the z direction.    
        bpy.ops.object.select_all(action = 'DESELECT')       
        Master.hide = False
        Master.show_transparent = False        
        bpy.context.scene.objects.active = Master
        Master.select = True        
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
        Master.rotation_mode = 'QUATERNION'        
        Master.rotation_quaternion = align        
        bpy.ops.object.transform_apply(location = True, rotation = True)
        Empty.parent = Master
        bpy.ops.view3d.viewnumpad(type = "TOP")
         
        return {'FINISHED'}
    
          
class DrawOccPlane(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.draw_occ_plane'
    bl_label = "Draw Occlusal Plane"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        
        
        sce=bpy.context.scene
        j = sce.splint_index
        splint = sce.splint[j]

        master = sce.master_model
        Master = sce.objects[master]       
        
        L = Master.location
        
        #Deselect everyone manualy since if they are
        #hidden the operator does not work
        for o in sce.objects:
            o.select = False
        
        for o in sce.objects:
            if o.name != master and not o.hide:
                o.hide = True
        

        
        Master.hide = False
        Master.select = True
        sce.objects.active = Master
        
        current_grease = [gp.name for gp in bpy.data.grease_pencil]
        print(current_grease)
        
        bpy.ops.gpencil.data_add()
        bpy.ops.gpencil.layer_add()
        
        for gp in bpy.data.grease_pencil:
            if gp.name not in current_grease:           
                print(gp.name)
                gplayer = gp.layers[0]
                gp.draw_mode = 'SURFACE'
                gp.name = 'occ_plane_indicator'
                gplayer.info = 'occ_plane_indicator'
                
        return {'FINISHED'}

class ThicknessCompensation(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.thickness_compensation'
    bl_label = "Thickness Compensation"
    bl_options = {'REGISTER','UNDO'}
    
    thickness = bpy.props.FloatProperty(name="Compensation", description="Amount to compensate for contraction in CT segmentation", default=.35, min=.01, max=1, step=5, precision=2, options={'ANIMATABLE'})
    
    def invoke(self,context,event):
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        
        sce=bpy.context.scene
        j = sce.splint_index
        splint = sce.splint[j]
        master = sce.master_model
        Master = sce.objects[master]
        
        for ob in sce.objects:
            ob.select = False
        
        Master.select = True
        Master.hide = False    
        sce.objects.active = Master
        
        n = len(Master.modifiers)
        bpy.ops.object.modifier_add(type = 'SOLIDIFY')
        
        mod = Master.modifiers[n]
        mod.thickness = self.thickness
        mod.offset = .75
        
        return {'FINISHED'}
       
class CalcPlane(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.calc_occ_plane'
    bl_label = "Calc Occ Plane"
    bl_options = {'REGISTER','UNDO'}
   

    def execute(self, context):
        bpy.context.tool_settings.mesh_select_mode = [True, False, False]
        sce=bpy.context.scene
        j = sce.splint_index
        splint = sce.splint[j]
        
        v3d = bpy.context.space_data
        v3d.pivot_point = 'MEDIAN_POINT'
        
        master = sce.master_model
        Master = sce.objects[master]
        Master.select = True
        Master.hide = False
        sce.objects.active = Master
        
        gp_plane = bpy.data.grease_pencil['occ_plane_indicator']
        bpy.ops.gpencil.convert(type = 'PATH')
        bpy.ops.object.convert(target = 'MESH')
        
        #the active object is now the mesh from gpencil stroke
        ob = bpy.context.object
        me = ob.data
        ob.name = 'Occlusal Plane'
        Oplane = ob
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.remove_doubles(mergedist = 5)
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        #if the user drew correctly, we should only have
        #3 vertices
        sel_verts = [v for v in me.vertices if v.select]
        if len(sel_verts) == 3:
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.edge_face_add()
            
            bpy.ops.mesh.subdivide()
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.context.tool_settings.mesh_select_mode = [False, True, False]
            v3d = bpy.context.space_data
            v3d.pivot_point = 'MEDIAN_POINT'
            
            bpy.ops.mesh.select_non_manifold()
            bpy.ops.mesh.select_all(action = 'INVERT')
            bpy.ops.transform.resize(value = (2,2,2))
            
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.flip_normals()
            
            
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
            
            bpy.ops.object.modifier_add(type = 'MULTIRES')
            
            for i in range(0,5):
                bpy.ops.object.multires_subdivide(modifier = 'Multires')
            
            bpy.ops.object.origin_set(type = 'ORIGIN_GEOMETRY')
            scale = Master.dimensions.length/Oplane.dimensions.length*2                   
            bpy.ops.transform.resize(value = (scale,scale,scale))        
            splint.plane = Oplane.name
            Oplane.parent = Master
            bpy.ops.transform.translate(value = (0,0,-5))
            
                  
        bpy.context.tool_settings.mesh_select_mode = [True, False, False]
        return{'FINISHED'}

class DrawSplintArchitecture(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.draw_splint_architecture'
    bl_label = "Draw Splint Architecture"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        
        
        sce=bpy.context.scene
        j = sce.splint_index
        splint = sce.splint[j]

        master = sce.master_model
        Master = sce.objects[master]       
        
        #Deselect everyone manualy since if they are
        #hidden the operator does not work
        for o in sce.objects:
            o.select = False
        
        for o in sce.objects:
            if o.name != master and not o.hide and o.name != splint.plane:                
                o.hide = True
        

        Master.select = True
        Master.hide = False
        sce.objects.active = Master
        
        
        
                
        current_objects = list(sce.objects)
        bpy.ops.mesh.primitive_plane_add()
        for o in sce.objects:
            if o not in current_objects:
                o.name = 'Splint'
                o.parent = Master
                splint.splint = o.name
                
        current_grease = [gp.name for gp in bpy.data.grease_pencil]
        print(current_grease)
        
        bpy.ops.gpencil.data_add()
        bpy.ops.gpencil.layer_add()
        
        for gp in bpy.data.grease_pencil:
            if gp.name not in current_grease:           
                print(gp.name)
                gplayer = gp.layers[0]
                gp.draw_mode = 'SURFACE'
                gp.name = 'osplint architecture'
                gplayer.info = 'splint architecture'
                
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.delete()        
        return {'FINISHED'}
    

class CalculateSplint(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.calculate_splint'
    bl_label = "Calculate Splint"
    bl_options = {'REGISTER','UNDO'}
    
    teeth = bpy.props.IntProperty(min=4, default=8)
    initial_off = bpy.props.FloatProperty(name="Initial Offset", description="increase if teeth not captured correctly!", default=1, min=.05, max=3, step=5, precision=2, options={'ANIMATABLE'})
    thickness = bpy.props.FloatProperty(name="Approx Thickness", description="Approximate thickness of the guide material, actual guide will be thicker", default=1.5, min=1, max=5, step=5, precision=2, options={'ANIMATABLE'})
    final_shift = bpy.props.FloatProperty(name="Upshift", description="Shift up thickens guide and ensures no intersections with teeth", default=1, min=.5, max=5, step=5, precision=2, options={'ANIMATABLE'})
    
    def invoke(self,context,event):
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
       
    def execute(self, context):
                
        sce=bpy.context.scene
        j = sce.splint_index
        splint = sce.splint[j]
        splint_model = splint.splint
        Splint_model = sce.objects[splint_model]
        
        master = sce.master_model
        Master = sce.objects[master]
        
        plane = splint.plane
        Plane = sce.objects[plane]
        
        #make the surface from the users marks
        ed_U = 4
        ed_V = self.teeth * 2
                
        #bpy.ops.gpencil.surfsk_add_surface('INVOKE_DEFAULT')
        sce.SURFSK_cyclic_cross = False
        sce.SURFSK_cyclic_follow = False
        sce.SURFSK_loops_on_strokes = False
        sce.SURFSK_cyclic_cross
        bpy.ops.gpencil.surfsk_add_surface('INVOKE_REGION_WIN',edges_U=ed_U, edges_V=ed_V, cyclic_cross=False, cyclic_follow=False, loops_on_strokes=False, automatic_join=False, join_stretch_factor=1)
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
        for o in sce.objects:
            o.select = False
            
        Splint_model.select = True
        sce.objects.active = Splint_model
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.context.tool_settings.mesh_select_mode = [True, False, False]
        bpy.ops.mesh.select_all(action = 'SELECT')
        
        #first, assignthe existing mesh to the "inside" group
        #from them we will construct the outside
        bpy.context.tool_settings.vertex_group_weight = 1
        
        n = len(Splint_model.vertex_groups)
        bpy.ops.object.vertex_group_add()
        Splint_model.vertex_groups[n].name = 'Inside'
        bpy.ops.object.vertex_group_assign()      
        
        #try to pull any of them up to the tooth surface        
        n = len(Splint_model.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Splint_model.modifiers[n]
        mod.wrap_method = 'PROJECT'
        mod.use_project_z = True
        mod.use_negative_direction = False
        mod.use_positive_direction = True
        mod.target = Master
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.modifier_apply(modifier = mod.name)
        
        #duplicate this mesh to use as a smooth
        #base to offset from since the tooth mesh
        #will inevitably have too much "topology"
        #and not give good results
        current_objects = list(bpy.data.objects)
        bpy.ops.object.duplicate()
        
        for o in sce.objects:
            if o not in current_objects:
                Approx = o
                Approx.select = False
                
        Splint_model.select = True
        sce.objects.active = Splint_model
        
        #offset from the approximation mesh
        n = len(Splint_model.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Splint_model.modifiers[n]
        mod.target = Approx
        mod.offset = self.initial_off
        mod.use_keep_above_surface = True
        
        bpy.ops.object.modifier_apply(modifier = mod.name)

        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        
        bpy.ops.mesh.extrude_region_move()
        
        #extruded vertices belong to the vgroup of the verst they were extruded from
        #so remove them
        bpy.ops.object.vertex_group_remove_from()
        
        #now lets give them their own group
        n = len(Splint_model.vertex_groups)
        bpy.ops.object.vertex_group_add()
        Splint_model.vertex_groups[n].name = 'Outside'
        bpy.ops.object.vertex_group_assign() 
        
        bpy.ops.transform.translate(value = (0,0,1))
        
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.normals_make_consistent()
        
        #bpy.ops.object.mode_set(mode = 'OBJECT')
        #bpy.ops.object.mode_set(mode = 'EDIT')
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        n = len(Splint_model.vertex_groups)
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.region_to_loop()
        bpy.context.tool_settings.mesh_select_mode = [True, False, False]
        bpy.ops.object.vertex_group_add()
        Splint_model.vertex_groups[n].name = 'Smooth'
        bpy.ops.object.vertex_group_assign()
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.vertex_group_set_active(group = 'Inside')
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.region_to_loop()
        bpy.context.tool_settings.mesh_select_mode = [True, False, False]
        bpy.ops.object.vertex_group_set_active(group = 'Smooth') 
        bpy.ops.object.vertex_group_assign()
        
        bpy.ops.object.mode_set(mode='OBJECT')
        
        n = len(Splint_model.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Splint_model.modifiers[n]
        mod.vertex_group = 'Outside'
        mod.target = Approx
        mod.offset = self.thickness
        mod.use_keep_above_surface = True
                
        bpy.ops.object.modifier_apply(modifier = mod.name)
        
        bpy.ops.transform.translate(value = (0,0,self.final_shift))
        
        
        bpy.ops.object.modifier_add(type = 'MULTIRES')
        for i in range(0,3):
            bpy.ops.object.multires_subdivide(modifier = 'Multires')
        
        
        n = len(Splint_model.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Splint_model.modifiers[n]
        mod.wrap_method = 'PROJECT'
        mod.use_project_z = True
        mod.use_negative_direction = True
        mod.use_positive_direction = True
        mod.target = Master
        mod.auxiliary_target = Plane
        mod.vertex_group = 'Inside'
        
        
        
        n = len(Splint_model.modifiers)
        bpy.ops.object.modifier_add(type = 'SMOOTH')
        mod = Splint_model.modifiers[n]
        mod.vertex_group = 'Smooth'
        mod.iterations = 5
        
        
        bpy.ops.object.select_all(action = 'DESELECT')
        sce.objects.active = Approx
        Approx.select = True
        bpy.ops.object.delete()
        
        return{'FINISHED'}
        
        
                       
class ImportAllImplants(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.import_all_implants'
    bl_label = "Import All Implants"
    bl_options = {'REGISTER','UNDO'}

    
    
    def execute(self, context):
        directory = bpy.context.scene.implant_lib
        things = os.listdir(directory)
        container = os.path.dirname(directory)
        
        implants = []
        for item in things:
            path = os.path.join(container,item)
            if os.path.isdir(path):
                implants.append(path)
            
        
        print(implants)
        
        for implant in implants:
            my_item = bpy.context.scene.library_implants.add()
            dir_name = implant
            imp_name = os.path.basename(dir_name)
            print(dir_name)
            print(imp_name)
            my_item.name = imp_name
            my_item.filepath = dir_name
            if 'hardware' in os.listdir(implant):
                print('hardware')
                my_item.hardware = True

        return {'FINISHED'}



class AppendLibraryImplant(bpy.types.Operator, ImportHelper):
    ''''''
    bl_idname = 'view3d.append_library_implant'
    bl_label = "Append Library Implant"
    bl_options = {'REGISTER','UNDO'}

    directory = StringProperty(subtype='DIR_PATH')
    
    def execute(self, context):

        my_item = bpy.context.scene.library_implants.add()
        
        print(self.directory)
        dir_name = os.path.dirname(self.directory)
        imp_name = os.path.basename(dir_name)

        my_item.name = imp_name
        
        my_item.filepath = dir_name
        
        if 'hardware' in os.listdir(self.directory):
            my_item.hardware = True

        return {'FINISHED'}
    
class RemoveLibraryImplant(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.remove_library_implant'
    bl_label = "Remove Library Implant"
        
    def execute(self, context):

        j = bpy.context.scene.library_implants_index
        bpy.context.scene.library_implants.remove(j)
                
        return {'FINISHED'}

class ClearLibrary(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.clear_library'
    bl_label = "Clear Library"
        
    def execute(self, context):
        sce = bpy.context.scene
        L = len(sce.library_implants)
        for j in range(0,L):
            bpy.context.scene.library_implants.remove(0)
                
        return {'FINISHED'}
################################################################################ 
class AppendWorkingImplant(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.append_working_space'
    bl_label = "Append Working Implant"
    bl_options = {'REGISTER','UNDO'}
    
    #We will select a tooth to work on
    teeth = [11,12,13,14,15,16,17,18,21,22,23,24,25,26,27,28,31,32,33,34,35,36,37,38,41,42,43,44,45,46,47,48]    
    teeth_enum=[]
    for index, o in enumerate(teeth):
        teeth_enum.append((str(index), str(o), str(index))) 
    ob_list = bpy.props.EnumProperty(name="Implant space to restore", description="A list of all teeth to chose from", items=teeth_enum, default='0')
    
    
    def invoke(self, context, event): 
        
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
    
    def execute(self, context):

        my_item = bpy.context.scene.working_space.add()
        indx = int(self.properties.ob_list)
        my_item.name = str(self.teeth[int(self.properties.ob_list)])
        
        return {'FINISHED'}
    
class RemoveWorkingImplant(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.remove_working_space'
    bl_label = "Remove Working Implant"
        
    def execute(self, context):

        j = bpy.context.scene.working_space_index
        bpy.context.scene.working_space.remove(j)
                
        return {'FINISHED'}
    
  
class  AddImplantParameters(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.add_implant_parameters'
    bl_label = "Add Implant Parameters"

    def execute(self, context):
        sce=bpy.context.scene
        
        #check for the existing properties
        eprops = [prop.name for prop in bpy.types.Scene.bl_rna.properties]
        
        bpy.types.Scene.implant_lib = bpy.props.StringProperty(
            name="Implant Library",
            default="C://",
            subtype='DIR_PATH')
        
        #if "Implant" not in bpy.data.scenes:
        #    n = len(bpy.data.scenes)
        #    bpy.ops.scene.new(type = 'NEW')
        #    new_sce = bpy.data.scenes[n]
        #    new_sce.name = 'Implant'        
        
        if "Master Model" not in eprops:        
            bpy.types.Scene.master_model = bpy.props.StringProperty(
                name="Master Model",
                default="")
                
        if "Opposing Model" not in eprops:
            bpy.types.Scene.opposing_model = bpy.props.StringProperty(
                name="Opposing Model",
                default="")    
        return {'FINISHED'}
    
class  AddImplantMaterials(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.add_implant_materials'
    bl_label = "Add Implant Materials"

    def execute(self, context):
        
        if 'implant_material' not in bpy.data.materials:
            
            bpy.data.materials.new(name = 'implant_material')
            mat = bpy.data.materials["implant_material"]
            mat.diffuse_color = Color((.687,.01,.04))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if 'bushing_material' not in bpy.data.materials:
                       
            bpy.data.materials.new(name = 'bushing_material')
            mat = bpy.data.materials["bushing_material"]
            mat.diffuse_color = Color((.6,.8,.6))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if 'orientation_material' not in bpy.data.materials:

            bpy.data.materials.new(name = 'orientation_material')
            mat = bpy.data.materials["orientation_material"]
            mat.diffuse_color = Color((.8,.5,.8))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if 'collision_material' not in bpy.data.materials:
                        
            bpy.data.materials.new(name = 'collision_material')
            mat = bpy.data.materials["collision_material"]
            mat.diffuse_color = Color((0,.5,.8))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if 'extension_material' not in bpy.data.materials:
            
            bpy.data.materials.new(name = 'extension_material')
            mat = bpy.data.materials["extension_material"]
            mat.diffuse_color = Color((.8,.5,.3))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True

        if 'aligner_material' not in bpy.data.materials:
            
            bpy.data.materials.new(name = 'aligner_material')
            mat = bpy.data.materials["aligner_material"]
            mat.diffuse_color = Color((.6,.02,.34))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if '50' not in bpy.data.materials:
            
            bpy.data.materials.new(name = '50')
            mat = bpy.data.materials["50"]
            mat.diffuse_color = Color((.75,.05,.8))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
        
        if '48' not in bpy.data.materials:
            
            bpy.data.materials.new(name = '48')
            mat = bpy.data.materials["48"]
            mat.diffuse_color = Color((1,.05,.05))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if '33' not in bpy.data.materials:
            
            bpy.data.materials.new(name = '33')
            mat = bpy.data.materials["33"]
            mat.diffuse_color = Color((.05,.8,.05))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if '41' not in bpy.data.materials:
            
            bpy.data.materials.new(name = '41')
            mat = bpy.data.materials["41"]
            mat.diffuse_color = Color((.8,.65,.05))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
                            
        return {'FINISHED'}
            
bpy.utils.register_class(AddImplantParameters)
bpy.ops.view3d.add_implant_parameters()
#class SetLibrary(bpy.types.Operator, ImportHelper):
class PlaceImplant(bpy.types.Operator):
    '''Place Implant'''
    bl_idname = "import_mesh.place_implant"
    bl_label = "Place Implant"
    bl_options = {'REGISTER','UNDO'}

  
    hardware = bpy.props.BoolProperty(name="Include Hardware", default=False)
    
    #def invoke(self, context, event): 

        #context.window_manager.invoke_props_dialog(self, width=300) 
        #return {'RUNNING_MODAL'}
    
    def execute(self, context):
        
        sce = bpy.context.scene
        j = sce.working_space_index
        space = sce.working_space[j]
        n = sce.library_implants_index
        library_implant = sce.library_implants[n]
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
        for ob in sce.objects:
            ob.select = False
            
        if space.implant:
            Implant = sce.objects[space.implant]
            Implant.hide = False
            Implant.select = True
            sce.objects.active = Implant
            
            if len(Implant.children):
                for child in Implant.children:
                    child.hide = False
                    child.select = True
            bpy.ops.object.delete()
            
        
        
        i_folder = library_implant.filepath
        if library_implant.hardware:
            hardware_folder = os.path.join(i_folder, 'hardware')
            hardware_files = [ fi for fi in os.listdir(hardware_folder) if fi.endswith(".stl") ]
        
        
        stl_files = [ fi for fi in os.listdir(i_folder) if fi.endswith(".stl") ]
        
        print(stl_files)
        print(hardware_files)
        
        
        if len(stl_files) > 1:
            self.report({'WARNING'}, "There should only be one STL file in the implant folder, the rest should be in a subfolder Harware")
            return{'CANCELLED'}
        
        #get a list of the materials in the blend file
        #we will use this to assign materials to imported
        #files if we can.        
        material_list=[]
        for mat in bpy.data.materials:
            material_list.append(mat.name)
        
        print(material_list)
        
        current_objects=list(sce.objects)  
            
        stl_path = os.path.join(i_folder,stl_files[0])
        bpy.ops.import_mesh.stl(filepath = stl_path)
        
        for o in sce.objects:
            if o not in current_objects:
                Implant = o
                
                #look for type of implant in the materials list
                for mat_name in material_list:
                    if mat_name in Implant.name:
                        print('the names match and the name is ' + Implant.name)
                        mat = bpy.data.materials[mat_name]
                
                if not mat:
                    print(Implant.name + "was not recognized as a preset, using generic color")
                    mat = bpy.data.materials["implant_material"]
                
                print(mat.name)    
                new_name = space.name + '_' + Implant.name
                Implant.name = new_name
                space.implant = new_name
                data = Implant.data               
                data.materials.append(mat)
        
        if self.hardware and 'hardware' in os.listdir(i_folder):
            for file in hardware_files:
                current_objects=list(sce.objects)  
                stl_path = os.path.join(hardware_folder,file)
                bpy.ops.import_mesh.stl(filepath = stl_path)
                bpy.ops.object.origin_set(type = 'ORIGIN_GEOMETRY')
                for o in sce.objects:
                    if o not in current_objects:
                        o.parent = Implant
                        imat_name = Implant.data.materials[0].name                     
                        #compare name of hardware to materials we have
                        #if any matches, assign material to it
                        mat = None
                        for mat_name in material_list:
                            #print(mat_name)
                            #print(o.name.lower())
                            if o.name.lower() in mat_name:
                                mat = bpy.data.materials[mat_name]
                            elif imat_name in ['33','41','48','50'] and ('moignon' in o.name.lower() or 'aligner' in o.name.lower()):
                                mat = bpy.data.materials[imat_name]
                        if mat:
                            data = o.data
                            data.materials.append(mat)
                            
                        new_name = space.name + '_' + o.name
                        o.name = new_name
                        o.show_transparent = True
                    
        bpy.ops.object.select_all(action = 'DESELECT')
        sce.objects.active = Implant
        Implant.select = True
        
        Implant.location = sce.cursor_location
        #for root, dirs, files in os.walk(i_folder):
            
            #stl_files = [ fi for fi in files if fi.endswith(".stl") ]
            
            #if len(stl_files) > 1:
                #self.report({'WARNING'}, "There should only be one STL file in the implant folder, the rest should be in a subfolder Harware")
                #return{'CANCELLED'}
            #print(files)
            #print(stl_files)
            
            #for file in stl_files:
            #stl_path = os.path.join(root,stl_files[0])
            #bpy.ops.import_mesh.stl(filepath = stl_path)
            
                  
            #if self.hardware:
                #if 'hardware' in root:
                    #stl_files = [ fi for fi in files if not fi.endswith(".stl") ]
                    #for file in stl_files:
                        
        return {'FINISHED'}
    
    
class GuideCylinder(bpy.types.Operator):
    '''Guide Cylinder'''
    bl_idname = "object.guide_cylinder"
    bl_label = "Guide Cylinder"
    bl_options = {'REGISTER','UNDO'}
    
    #channel = bpy.props.BoolProperty(name="Channel", default=False)
    use_plane = bpy.props.BoolProperty(name="Use Plane", default=False)
    cutout = bpy.props.BoolProperty(name="Cutout Plane", default=False)
    #inner = bpy.props.FloatProperty(name="Slice Thickness", description="view slice thickenss", default=1, min=1, max=10, step=5, precision=2, options={'ANIMATABLE'})
    thickness = bpy.props.FloatProperty(name="Cylinder Thickness", description="width in addition to the diameter of the implant", default=1, min=1, max=5, step=5, precision=1, options={'ANIMATABLE'})
    depth = bpy.props.FloatProperty(name="Top Edge to Apex of Implant", description="", default=15, min=10, max=30, step=5, precision=2, options={'ANIMATABLE'})
    length = bpy.props.FloatProperty(name="Length", description="make sure this enters into guide", default=5, min=1, max=10, step=5, precision=2, options={'ANIMATABLE'})
    
    def invoke(self, context, event): 
               
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
    
    def execute(self,context):
        
        sce = bpy.context.scene
        j = sce.working_space_index
        space = sce.working_space[j]

        
                    
        for ob in sce.objects:
            ob.select = False
            
        if not space.implant:
            self.report({'WARNING'}, "It seems you have not yet placed an implant...let's not get ahead of ourselves.  Please place an implant before switching")
        
        Implant = sce.objects[space.implant]
        D = Implant.dimensions[0]
        
        L = Implant.location.copy()
        mx_b = Implant.matrix_basis.copy()
        mx_w = Implant.matrix_world.copy()
        mx_l = Implant.matrix_local.copy()
        
        sce.cursor_location = L
        
        current_objects=list(sce.objects)
        
        bpy.ops.mesh.primitive_circle_add()
        
        name = Implant.name + '_GC'
        
        for o in sce.objects:
            if o not in current_objects:
                o.name = name
                #o.parent = Implant
                
                o.matrix_world = mx_w
                o.matrix_basis = mx_b
                o.matrix_local = mx_l
                o.location = L
                Cylinder = o
        #get the space data
        v3d = bpy.context.space_data

        #set the transform orientation and pivot point
        v3d.transform_orientation = 'LOCAL'
        v3d.pivot_point = 'MEDIAN_POINT'
              
        #editmode
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        #Get the angulation of the implant
        quat = mx_w.to_quaternion()
        T = quat*Vector((0,0,-self.depth))
        t = quat*Vector((0,0, self.length))
        S = quat*Vector((1,1,0))
        
        #Translate top of cylinder to level of bit
        bpy.ops.transform.translate(value=(T[0], T[1], T[2]), constraint_axis=(False, False, False), constraint_orientation='LOCAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)
        
        #this will be the final radius of the cylinder
        #D is the diameter of the implant.
        A = D/2 + self.thickness
        V = Vector((A, A, A))
        bpy.ops.transform.resize(value = (V[0],V[1],V[2]))
        
        #fill in the circle..alternatively, with  bmesh, we could just make a face? not sure how this works yet
        bpy.ops.mesh.extrude_edges_move()
        bpy.ops.transform.resize(value = (0,0,0))
        bpy.ops.mesh.remove_doubles(mergedist=0.0001)
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.extrude_region_move()
        
        #translate the bottom by the thickness
        bpy.ops.transform.translate(value = (t[0],t[1],t[2]))
        
        bpy.context.tool_settings.vertex_group_weight = 1
        n=len(Cylinder.vertex_groups)
        bpy.ops.object.vertex_group_add()
        bpy.ops.object.vertex_group_assign(new = False)
        group = Cylinder.vertex_groups[n]
        group.name = 'Lower'
        
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.normals_make_consistent()
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        n = len(Cylinder.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Cylinder.modifiers[n]
        mod.wrap_method = 'PROJECT'
        mod.use_project_z = True
        mod.use_project_y = False
        mod.use_project_x = False
        mod.use_negative_direction = True
        mod.use_positive_direction = True
        mod.offset = -.2
        
        
        if self.use_plane:
            k = sce.splint_index
            splint = sce.splint[k]
            plane = splint.plane
            if splint.plane:
                mod.vertex_group = 'Lower'
                mod.target = sce.objects[plane]
        
        
        
        if self.cutout:
            current_objects = list(sce.objects)
            bpy.ops.mesh.primitive_plane_add()
            for o in sce.objects:
                if o not in current_objects:
                    o.name = Implant.name + "_Cutout"
                    bpy.ops.transform.resize(value = (D/2+self.thickness, 2*D, 0))
                    bpy.ops.object.transform_apply(scale = True)
                    o.matrix_world = mx_w
                    o.matrix_basis = mx_b
                    o.matrix_local = mx_l
                    o.location = L
                    Cutout = sce.objects[o.name]
                    bpy.ops.transform.translate(value=(T[0], T[1], T[2]), constraint_axis=(False, False, False), constraint_orientation='LOCAL', mirror=False, proportional='DISABLED', proportional_edit_falloff='SMOOTH', proportional_size=1)
                    Cutout.select = True
                    space.cutout = Cutout.name
                    
        Implant.select = True
        Implant.hide=False
        Cylinder.select = True
        
        sce.objects.active = Implant
        bpy.ops.object.parent_set(type = 'OBJECT')
        Cylinder.select = False
        
        if self.cutout:
            Cutout.select = False      
        space.outer = Cylinder.name            
        
        #color the cylinder
        me = Cylinder.data
        mat = bpy.data.materials['bushing_material']
        me.materials.append(mat)                
                 
        return {'FINISHED'}


class InnerCylinder(bpy.types.Operator):
    '''Inner Cylinder'''
    bl_idname = "object.inner_cylinder"
    bl_label = "Inner Cylinder"
    bl_options = {'REGISTER','UNDO'}
    
    channel = bpy.props.BoolProperty(name="Channel", default=False)
    channelpct = bpy.props.FloatProperty(name="Percentage", description="", default=5, min=1, max=20, step=5, precision=1, options={'ANIMATABLE'})
    diameter = bpy.props.FloatProperty(name="Inner Cylinder Diameter", description="", default=1, min=1, max=7, step=5, precision=1, options={'ANIMATABLE'})
    
    
    def execute(self,context):
        
        sce = bpy.context.scene
        j = sce.working_space_index
        space = sce.working_space[j]

        
                    
        for ob in sce.objects:
            ob.select = False
            
        if not space.implant:
            self.report('WARNING', "It seems you have not yet placed an implant...let's not get ahead of ourselves.  Pleaes place an implant before switching")
        
        Implant = sce.objects[space.implant]
        D = Implant.dimensions[0]
        
        L = Implant.location.copy()
        mx_b = Implant.matrix_basis.copy()
        mx_w = Implant.matrix_world.copy()
        mx_l = Implant.matrix_local.copy()
        
        sce.cursor_location = L
        
        current_objects=list(sce.objects)
        
        bpy.ops.mesh.primitive_circle_add()
        
        name = Implant.name + '_IC'
        
        for o in sce.objects:
            if o not in current_objects:
                o.name = name
                #o.parent = Implant
                
                o.matrix_world = mx_w
                o.matrix_basis = mx_b
                o.matrix_local = mx_l
                o.location = L
                Cylinder = o
        #get the space data
        v3d = bpy.context.space_data

        #set the transform orientation and pivot point
        v3d.transform_orientation = 'LOCAL'
        v3d.pivot_point = 'MEDIAN_POINT'
              
        #editmode
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        #Get the angulation of the implant
        quat = mx_w.to_quaternion()
        T = quat*Vector((0,0,-30))

        V = Vector((self.diameter/2, self.diameter/2, self.diameter/2))
        bpy.ops.transform.resize(value = (V[0],V[1],V[2]))
        
        #extrude the circle and collapse the verts into the center
        bpy.ops.mesh.extrude_edges_move()
        bpy.ops.transform.resize(value = (0,0,0))
        bpy.ops.mesh.remove_doubles(mergedist=0.0001)
        
        if self.channel:
            bpy.ops.mesh.select_all(action = 'DESELECT')
            
            verts = [0,1,8,9,16,17,24,25]
            bpy.ops.object.mode_set(mode = 'OBJECT')
            for v in verts:
                Cylinder.data.vertices[v].select = True
                
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.extrude_edges_move()
            A = (100+self.channelpct)/100
            bpy.ops.transform.resize(value = (A,A,A))
                    
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.extrude_region_move()
        
        bpy.ops.transform.translate(value = (T[0],T[1],T[2]))
        
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.normals_make_consistent()
               
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        Implant.select = True
        Implant.hide = False
        Cylinder.select = True
        
        sce.objects.active = Implant
        bpy.ops.object.parent_set(type = 'OBJECT')
        Cylinder.select = False        
        space.inner = Cylinder.name
        
        #color the cylinders
        me = Cylinder.data
        mat = bpy.data.materials['extension_material']
        me.materials.append(mat)
        
                 
        return {'FINISHED'}
    
class Cutouts(bpy.types.Operator):
    '''Cutouts'''
    bl_idname = "object.cutouts"
    bl_label = "Cutouts"
    bl_options = {'REGISTER','UNDO'}
    
    before = bpy.props.BoolProperty(name="Before Multires", default=False)
    
    def execute(self,context):
        
        sce = bpy.context.scene
        k = sce.splint_index
        splint = sce.splint[k]
        splint_model = splint.splint
        
        for ob in sce.objects:
            ob.select = False
            
        for space in sce.working_space:
            if space.cutout:
                Cutout = sce.objects[space.cutout]
                Cutout.select = True
                Cutout.hide = False
                sce.objects.active = Cutout
                
        current_objects = list(sce.objects)
        
        bpy.ops.object.duplicate()
        
        #if there are multipl implants, we will need to join their guide cylinders
        if len(bpy.context.selected_editable_objects) > 1:
            bpy.ops.object.join()
            
        for ob in sce.objects:
            if ob not in current_objects:
                ob.name = 'Cutouts'
                Cutouts = sce.objects['Cutouts']
                bpy.ops.object.parent_clear(type = 'CLEAR_KEEP_TRANSFORM')
                
        Splint = sce.objects[splint_model]
        
        sce.objects.active = Splint
        Splint.hide = False
        Splint.select = True
        
        n = len(Splint.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Splint.modifiers[n]
        mod.wrap_method = 'PROJECT'
        mod.use_project_z = True
        mod.use_negative_direction = True
        mod.use_positive_direction = False
        mod.vertex_group = 'Outside'
        mod.target = Cutouts
        mod.name = 'Cutout'
        
        if self.before:
            for i in range(0,n):
                bpy.ops.object.modifier_move_up(modifier = 'Cutout')
        
        Cutouts.hide = True
        
        for space in sce.working_space:
            if space.cutout:
                Cutout = sce.objects[space.cutout]
                Cutout.hide = True
                  
        return {'FINISHED'}
    
class PrepareSculpt(bpy.types.Operator):
    '''Prepare Sculpt'''
    bl_idname = "object.prepare_sculpt"
    bl_label = "Prepare Sculpt"
    bl_options = {'REGISTER','UNDO'}
    
    
    def execute(self,context):
        
        sce = bpy.context.scene
        k = sce.splint_index
        splint = sce.splint[k]
        splint_model = splint.splint
        
        for ob in sce.objects:
            ob.select = False
                
        Splint = sce.objects[splint_model]
        
        sce.objects.active = Splint
        Splint.select = True
        
        for mod in Splint.modifiers:
            if mod.type != 'MULTIRES':
                bpy.ops.object.modifier_apply(modifier = mod.name)
                
        bpy.context.tool_settings.sculpt.use_symmetry_x = False
        bpy.context.tool_settings.sculpt.use_symmetry_y = False
        bpy.context.tool_settings.sculpt.use_symmetry_z = False
                 
        return {'FINISHED'}
    
            
class MergeGuides(bpy.types.Operator):
    '''Merge Guides'''
    bl_idname = "object.merge_guides"
    bl_label = "Merge Guides"
    bl_options = {'REGISTER','UNDO'}
    
    
    def execute(self,context):
        
        sce = bpy.context.scene
        k = sce.splint_index
        splint = sce.splint[k]
        splint_model = splint.splint
        
        for ob in sce.objects:
            ob.select = False
            
        for space in sce.working_space:
            if space.outer:
                Outer = sce.objects[space.outer]
                Outer.select = True
                Outer.hide = False
                sce.objects.active = Outer
                
        current_objects = list(sce.objects)
        
        bpy.ops.object.duplicate()
        
        #if there are multipl implants, we will need to join their guide cylinders
        if len(bpy.context.selected_editable_objects) > 1:
            bpy.ops.object.join()
            
        for ob in sce.objects:
            if ob not in current_objects:
                ob.name = 'Guides'
                Guides = sce.objects['Guides']
                bpy.ops.object.parent_clear(type = 'CLEAR_KEEP_TRANSFORM')
                
        Splint = sce.objects[splint_model]
        
        sce.objects.active = Splint
        Splint.select = True
        
        n = len(Splint.modifiers)
        bpy.ops.object.modifier_add(type = 'BOOLEAN')
        mod = Splint.modifiers[n]
        mod.operation = 'UNION'
        mod.object = Guides          
        
        Guides.hide = True
        
        for space in sce.working_space:
            if space.outer:
                Outer = sce.objects[space.outer]
                Outer.hide = True
                  
        return {'FINISHED'}
    
    
class SubtractHoles(bpy.types.Operator):
    '''Subtract Holes'''
    bl_idname = "object.subtract_holes"
    bl_label = "Subtract Holes"
    bl_options = {'REGISTER','UNDO'}
    
    
    def execute(self,context):
        
        sce = bpy.context.scene
        k = sce.splint_index
        splint = sce.splint[k]
        splint_model = splint.splint
        
        for ob in sce.objects:
            ob.select = False
            
        for space in sce.working_space:
            if space.inner:
                Inner = sce.objects[space.inner]
                Inner.select = True
                Inner.hide = False
                sce.objects.active = Inner
                
        current_objects = list(sce.objects)
        
        bpy.ops.object.duplicate()
        
        #if there are multipl implants, we will need to join their holes
        if len(bpy.context.selected_editable_objects) > 1:
            bpy.ops.object.join()
        for ob in sce.objects:
            if ob not in current_objects:
                ob.name = 'Holes'
                Holes = sce.objects['Holes']
                bpy.ops.object.parent_clear(type = 'CLEAR_KEEP_TRANSFORM')
        
        Splint = sce.objects[splint_model]
        
        sce.objects.active = Splint
        Splint.select = True
        
        n = len(Splint.modifiers)
        bpy.ops.object.modifier_add(type = 'BOOLEAN')
        mod = Splint.modifiers[n]
        mod.operation = 'DIFFERENCE'
        mod.object = Holes      

        Holes.hide = True
        
        for space in sce.working_space:
            if space.inner:
                Inner = sce.objects[space.inner]
                Inner.hide = True
                
                
        return {'FINISHED'}   
        
class SwapImplant(bpy.types.Operator):
    '''Swap Implant'''
    bl_idname = "import_mesh.swap_implant"
    bl_label = "Swap Implant"
    bl_options = {'REGISTER','UNDO'}

  
    hardware = bpy.props.BoolProperty(name="Include Hardware", default=False)
    
    #def invoke(self, context, event): 

        #context.window_manager.invoke_props_dialog(self, width=300) 
        #return {'RUNNING_MODAL'}
    
    def execute(self, context):
        
        sce = bpy.context.scene
        j = sce.working_space_index
        space = sce.working_space[j]
        n = sce.library_implants_index
        library_implant = sce.library_implants[n]
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
        for ob in sce.objects:
            ob.select = False
            
        if not space.implant:
            self.report('WARNING', "It seems you have not yet placed an implant...let's not get ahead of ourselves.  Pleaes place an implant before switching")
        
        Implant = sce.objects[space.implant]
        Implant.hide = False
        Implant.select = True
        sce.objects.active = Implant
        
        print(Implant.parent)
        parent = None
        if Implant.parent:
            parent = Implant.parent.name
            Parent = sce.objects[parent]
            
        L = Implant.location.copy()
        mx_b = Implant.matrix_basis.copy()
        mx_w = Implant.matrix_world.copy()
        mx_l = Implant.matrix_local.copy()
            
        if len(Implant.children):
            for child in Implant.children:
                child.hide = False
                child.select = True
        bpy.ops.object.delete()
            
        

        i_folder = library_implant.filepath
        if library_implant.hardware:
            hardware_folder = os.path.join(i_folder, 'hardware')
            hardware_files = [ fi for fi in os.listdir(hardware_folder) if fi.endswith(".stl") ]
        
        
        stl_files = [ fi for fi in os.listdir(i_folder) if fi.endswith(".stl") ]
        
        print(stl_files)
        print(hardware_files)
        
        
        if len(stl_files) > 1:
            self.report('WARNING', "There should only be one STL file in the implant folder, the rest should be in a subfolder Harware")
            return{'CANCELLED'}
        
        #get a list of the materials in the blend file
        #we will use this to assign materials to imported
        #files if we can.        
        material_list=[]
        for mat in bpy.data.materials:
            material_list.append(mat.name)
        
        print(material_list)
        
        current_objects=list(sce.objects)  
            
        stl_path = os.path.join(i_folder,stl_files[0])
        bpy.ops.import_mesh.stl(filepath = stl_path)
        
        for o in sce.objects:
            if o not in current_objects:
                Implant = o
                
                #look for type of implant in the materials list
                for mat_name in material_list:
                    if mat_name in Implant.name:
                        print('the names match and the name is ' + Implant.name)
                        mat = bpy.data.materials[mat_name]
                
                if not mat:
                    print(Implant.name + "was not recognized as a preset, using generic color")
                    mat = bpy.data.materials["implant_material"]
                
                print(mat.name)    
                new_name = space.name + '_' + Implant.name
                Implant.name = new_name
                space.implant = new_name
                data = Implant.data               
                data.materials.append(mat)
        
        if self.hardware and 'hardware' in os.listdir(i_folder):
            for file in hardware_files:
                current_objects=list(sce.objects)  
                stl_path = os.path.join(hardware_folder,file)
                bpy.ops.import_mesh.stl(filepath = stl_path)
                bpy.ops.object.origin_set(type = 'ORIGIN_GEOMETRY')
                for o in sce.objects:
                    if o not in current_objects:
                        o.parent = Implant
                        imat_name = Implant.data.materials[0].name                     
                        #compare name of hardware to materials we have
                        #if any matches, assign material to it
                        mat = None
                        for mat_name in material_list:
                            #print(mat_name)
                            #print(o.name.lower())
                            if o.name.lower() in mat_name:
                                mat = bpy.data.materials[mat_name]
                            elif imat_name in ['33','41','48','50'] and ('moignon' in o.name.lower() or 'aligner' in o.name.lower()):
                                mat = bpy.data.materials[imat_name]
                        if mat:
                            data = o.data
                            data.materials.append(mat)
                            
                        new_name = space.name + '_' + o.name
                        o.name = new_name
                        o.show_transparent = True
                    
        bpy.ops.object.select_all(action = 'DESELECT')
        sce.objects.active = Implant
        Implant.select = True
        
        if parent:
            Implant.parent = Parent
           
        Implant.matrix_world = mx_w
        Implant.matrix_basis = mx_b
        Implant.matrix_local = mx_l
        Implant.location = L

        return {'FINISHED'}
    
class HideHardware(bpy.types.Operator):
    '''Hide Hardware'''
    bl_idname = "view3d.hide_hardware"
    bl_label = "Hide Hardware"
    bl_options = {'REGISTER','UNDO'}

  
    unhide = bpy.props.BoolProperty(name="Unhide Hardware", default=False)
    
    def execute(self, context):
        
        sce = bpy.context.scene
        j = sce.working_space_index
        space = sce.working_space[j]
        implant = space.implant
        if not implant:
            self.report('WARNING',"There is no implant associated with this edentulous space!")
            return {'CANCELLED'}
        
        Implant = sce.objects[implant]        
        if not len(Implant.children):
            self.report('WARNING',"There is no hardware associated with the active edentulous space")
            return {'CANCELLED'}
        
        hidden = False == self.unhide
        for child in Implant.children:
            child.hide = hidden
                            
        return {'FINISHED'}
   
class SliceView(bpy.types.Operator):
    '''Tooltip'''
    bl_idname = "view3d.slice_view"
    bl_label = "Slice View"
    bl_options = {'REGISTER','UNDO'}
    
    thickness = bpy.props.FloatProperty(name="Slice Thickness", description="view slice thickenss", default=1, min=1, max=10, step=5, precision=2, options={'ANIMATABLE'})
    def execute(self,context):
        
        view = bpy.context.space_data
        
        view.clip_end = view.clip_start + self.thickness
        
        
        if not view.region_quadview:
            bpy.ops.screen.region_quadview()
            
                           
        return{'FINISHED'}

  
class NormalView(bpy.types.Operator):
    '''Tooltip'''
    bl_idname = "view3d.normal_view"
    bl_label = "Normal View"
    bl_options = {'REGISTER','UNDO'}
    
    thickness = bpy.props.FloatProperty(name="Slice Thickness", description="view slice thickenss", default=1, min=1, max=10, step=5, precision=2, options={'ANIMATABLE'})
    def execute(self,context):
        
        view = bpy.context.space_data        
        view.clip_end = view.clip_start + 10000
        
        
        if view.region_quadview:
            bpy.ops.screen.region_quadview()
            
                           
        return{'FINISHED'}
    
      
class CenterAllObjects(bpy.types.Operator):
    '''Use With Caution especially if objects are parented.'''
    bl_idname = "view3d.center_objects"
    bl_label = "Center In Scene"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self,context):
        sce = bpy.context.scene
        #gather all the objects
        objects = [ob for ob in sce.objects] #don't want this to update
        
        #put all their origins at their medianpoint
        bpy.ops.object.select_all(action='DESELECT')
        for ob in objects:
            sce.objects.active = ob
            ob.hide = False
            ob.select = True
            bpy.ops.object.origin_set(type = 'ORIGIN_GEOMETRY', center = 'BOUNDS')
            ob.select = False
            
        #calculate the median point of all the objects
        Med = Vector((0,0,0))
        for ob in objects:
            Med += ob.location
        Med = 1/len(objects)*Med
        print(Med)
        
        #Move everyone
        bpy.ops.object.select_all(action = 'SELECT')
        bpy.ops.transform.translate(value = (-Med[0], -Med[1], -Med[2]))
        
        #celebrate                           
        return{'FINISHED'}
    
    
class GoToFixed(bpy.types.Operator):

    ''''''
    bl_idname = 'view3d.go_to_fixed'
    bl_label = "Go To Fixed"
    bl_options = {'REGISTER','UNDO'}   
    
    """ 
    This takes the relevant info from your implant planning and
    puts it in a new scene and established the correct spatial
    relationships for desiging provisionals or custom abbutments
    """
        #A note on layers organization
        #Layer 0 will be our master layer, everything is in it.
        #if we are just doing restorative or just implant planning
        #there is no need to utilize the other layers
        
        #1. All fixed items  (models, preps, margins)
        #2. All Implant objects (bone, implants, hardware etc)
        #3. Just Bone
        #4. Just Intraoral Scans
        #5. Just Preps
        #6. Just Implants with Abutments (no other hardware)
        #7. just Restorations 
    
    def execute(self, context):
        
        sce=bpy.context.scene
        bpy.ops.object.select_all(action = 'DESELECT')
        
        hidden = [ob for ob in sce.objects if ob.hide]
        selected = [ob for ob in sce.objects if ob.select]
        
        #Get the materials
        mat1=bpy.data.materials["prep_material"]
        mat2=bpy.data.materials["opposing_material"]
        
        #the master model should be an intraoral scan and in the
        #fixed restorative layer
        master=sce.master_model
        Master=sce.objects[master]
        Master.layers[1] = True
                
        #Assing the material to it's data    
        me1=Master.data
        me1.materials.append(mat1)
        Master.show_transparent = True
        
        #Do the same for the opposing model if there is one.
        if sce.opposing_model:
            opposing=sce.opposing_model
            Opposing=sce.objects[opposing] 
            Opposing.layers[1] = True           
            me2=Opposing.data
            me2.materials.append(mat2)
            Opposing.show_transparent = True        
            Opposing.hide=True
            
            
        for A in bpy.context.window.screen.areas:
            if A.type == 'VIEW_3D':
                for s in A.spaces:
                    if s.type == 'VIEW_3D':
                        s.pivot_point = 'CURSOR'
                        
        implant_objects = []
        #link the implants themselves to the fixed layer.
        for space in sce.working_space:
            if space.implant:
                Implant = bpy.data.objects[space.implant]
                Implant.layers[6] = True
                implant_objects.append(Implant.name)
                if Implant.children:
                    for child in Implant.children:
                        if "Aligner" in child.name or "Abutment" in child.name:
                            child.layers[6] = True
            
        #parent everyone to the master (except implant hardware)
        #in the future...we may need to investigate the abutments!
        bpy.ops.object.select_all(action = 'DESELECT')
        for ob in sce.objects:
            if ob.name != master and not ob.parent:
                ob.hide = False
                ob.select = True
                if ob.name != sce.opposing_model:
                    dat = ob.data
                    if len(dat.materials) == 0:
                        dat.materials.append(mat1)
        
        Master.select = True
        sce.objects.active=Master
        bpy.ops.object.parent_set(type = 'OBJECT')
                
        bpy.ops.view3d.snap_cursor_to_center()
        T=bpy.context.object.location*-1
        bpy.ops.transform.translate(value=T)
       
        bpy.ops.view3d.viewnumpad(type='TOP')        
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle()
        
        sce.layers[0] = False
        sce.layers[1] = True
        sce.layers[6] = True
        
        bpy.ops.object.select_all(action = 'DESELECT')
        
        for ob in hidden:
            ob.hide = True
            
        for ob in selected:
            ob.select = True 
        #go to the fixed scene.
        #bpy.context.screen.scene = sce_fixed
        
        
             
        return {'FINISHED'}
    
    
##########################################
#######    Panels         ################
##########################################

class View3DPanel2():
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'


class ImplantLibPanel(View3DPanel2, bpy.types.Panel):
    bl_label = "Implant Library"
    bl_context = ""

    def draw(self, context):
        sce = bpy.context.scene
        layout = self.layout
                
        row = layout.row()
        row.prop(sce,"implant_lib")
        
        row = layout.row()
        row.template_list(sce, "library_implants", sce, "library_implants_index")
        
        col = row.column(align=True)
        col.operator("view3d.import_all_implants", text = "Import all Implants")
        col.operator("view3d.append_library_implant", text = "Import an Implant")
        col.operator("view3d.clear_library", text = "Clear Library")
        col.operator("view3d.remove_library_implant", text = "Remove an Implant")
        
        
        
        
class View3DPanel():
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'


class ImplantPanel(View3DPanel, bpy.types.Panel):
    bl_label = "Implant Tools"
    bl_context = ""

    def draw(self, context):
        sce = bpy.context.scene
        layout = self.layout
        
        
        #split = layout.split()

        #row = layout.row()
        #row.label(text="By Patrick Moore and others...")
        #row.operator("wm.url_open", text = "", icon="QUESTION").url = "https://sites.google.com/site/blenderdental/contributors"
        
        row = layout.row()
        row.label(text = "Edentulous Spaces to Fill")
        row = layout.row()
        row.template_list(sce, "working_space", sce, "working_space_index")
        
        col = row.column(align=True)
        col.operator("view3d.append_working_space", text = "Add a Space")
        col.operator("view3d.remove_working_space", text = "Remove a Space")
        #col.template_list(sce, "library_implants", sce, "library_implants_index",rows =2, maxrows = 2)
        
        row = layout.row()
        row.operator("view3d.center_objects")
        
        row = layout.row()
        row.operator("view3d.slice_view")
        
        row = layout.row()
        row.operator("view3d.normal_view")
        
        row = layout.row()
        row.operator("import_mesh.place_implant")
        
        row = layout.row()
        row.operator("import_mesh.swap_implant")
        
        row = layout.row()
        row.operator("view3d.hide_hardware")
        
        row = layout.row()
        row.operator("object.guide_cylinder")
        
        row = layout.row()
        row.operator("object.inner_cylinder")
        
        #check for the existing properties
        eprops = [prop.name for prop in sce.bl_rna.properties]
        
        if "Master Model" in eprops:
            
            row = layout.row()
            row.operator("view3d.set_master",text="Make Master")
            
            row=layout.column(align=True)
            row.operator("view3d.set_opposing",text="Make Opposing")
            
            row=layout.column(align=True)
            row.operator("view3d.go_to_fixed",text="Process for Fixed")
            
class VIEW3D_PT_SplintDesign(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="TOOLS"
    bl_label = "Splint Design"
    bl_context =  ""
    
    
    
    
    
    def draw(self, context):
        sce = context.scene
        layout = self.layout
        #split = layout.split()

        row = layout.row()
        row.label(text="By Patrick Moore and others...")
        row.operator("wm.url_open", text = "", icon="QUESTION").url = "https://sites.google.com/site/blenderdental/contributors"
        
        row = layout.row()
        row.template_list(sce, "splint", sce, "splint_index")
        
        col = row.column(align=True)
        col.operator("view3d.append_splint", text = "Add")
        col.operator("view3d.remove_splint", text = "Remove")
        
        row = layout.row()
        row.operator("view3d.thickness_compensation", text = "Thickness Compensation")
        
        row = layout.row()
        row.operator("view3d.define_splint_axis", text = "Define Axis")
        
        row = layout.row()
        row.operator("view3d.draw_occ_plane", text = "Mark Plane")
        
        row = layout.row()
        row.operator("view3d.calc_occ_plane", text = "Calc Plane")
        
        row = layout.row()
        row.operator("view3d.draw_splint_architecture", text = "Draw Splint Architecture")
        
        row = layout.row()
        row.operator("view3d.calculate_splint", text = "Calculate Splint")
        
        row = layout.row()
        row.operator("object.cutouts", text = "Cutouts")
        
        row = layout.row()
        row.operator("object.prepare_sculpt", text = "Prepare Sculpt")
                
        row = layout.row()
        row.operator("object.merge_guides", text = "Add Guides")
        
        row = layout.row()
        row.operator("object.subtract_holes", text = "Subtract Holes")
        
        
classes = ([PlaceImplant,ImplantPanel, ImplantLibPanel, SliceView, NormalView, AddImplantMaterials, AppendWorkingImplant, RemoveWorkingImplant, AppendLibraryImplant, RemoveLibraryImplant,CenterAllObjects,ImportAllImplants,GoToFixed, HideHardware,
            ThicknessCompensation, AppendSplint, RemoveSplint, DefineSplintAxis, DrawOccPlane, CalcPlane, DrawSplintArchitecture,CalculateSplint,VIEW3D_PT_SplintDesign,SwapImplant,GuideCylinder,InnerCylinder,SubtractHoles,MergeGuides,Cutouts, ClearLibrary,PrepareSculpt])

    
        
def register():
        
    for c in classes:
        bpy.utils.register_class(c)
       
    bpy.ops.view3d.add_implant_materials()

    
def unregister():
    
    for c in classes:
        bpy.utils.unregister_class(c)
        
if __name__ == "__main__": 
    register()