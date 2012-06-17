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
    'name': "Open Dental CAD for Blender",
    'author': "Patrick R. Moore",
    'version': (1,0,2),
    'blender': (2, 6, 3),
    'api': 47515,
    'location': "3D View -> Tool Shelf",
    'description': "10/25/2011 Version",
    'warning': "",
    'wiki_url': "http://dentallabnetwork.com/forums/f33/designing-restoration-free-open-source-6466/index2.html",
    'tracker_url': "",
    'category': '3D View'}


import bpy
from math import *
from mathutils import *
from mathutils import Vector
import time





## Changes in Rev. 1.0.1 8/28/2011
    #- Added a margin finding feature based on the grease pencil and the 
    #  shrinkwrap modifier
    
    #- Made appropriate changes to UI
    
    #- Fixed the left side tooth library normals
    
    #- Fixed a bug with the tooth rotation when inserting library template
    
    #- Added some tool setting conveniences between steps
    
    #- Added a step to make the normals between the intaglio and the
    #  crown form consistent in the final restoration.
    
## Changes in Rev 1.0.1 8/29/2011
    #- Added function "Coping from Crown" with user or automatically defined
    #  cutback and support.
    
    #- Made the way in which the add on keeps track of the different meshes
    #  more intuitive.  For exmaple, if a restoration starts off as a simple
    #  coping, but then the user want's it to be an anatomic coping halway
    #  through the case, making that change will not affect the steps which 
    #  are required for both types of restoration.
    
## Changes in Rev 1.0.1 9/14/2011
    #- Added function "Coping from Crown" into UI    
    #- Streamlined UI based on restoration type, eliminating excess options
    #  but leaving the option to show all functions anyway.

## Changes in Rev 1.0.1 9/15/2011
    #- Learned how to place warnings and errors    
    #- Improved the hanling of going into sculp/waxing
    
## Changes in Rev 1.0.1 9/23/2011
    #- Added a rough update function to the "working tooth index" property   
    #- Experimented with using multpile insertion axes and storing their
    #  transfrom instead of having to set the master model.  This will also
    #  help with less parenting issues...but may cuase problems for some of
    #  my other scripts which rely on the local and world coordinate being
    #  aligned
    #- Added tooth.psuedomargin to the working teeth property group

## Changes in Rev 1.0.1 9/28/2011
    #- Added initial support for simultaneous implant planning directly into
    #  implant intaglio or onto a custom abutment.  Proper parenting for both
    #  can be adjusted using the "abutment" option in define prep  
    
    
## Changes in Rev 1.0.1 9/29/2011
    #- Revisited the idea of generalized insertion axes for each restoration.
    #  Instead, I have made a function which essentially hybridizes the current
    #  and new system.  It takes the current view, and rotates the object such
    #  that when viewed from global z, it is the same as the current view. 
    
## Changes in Rev 1.0.1 10/04/2011
    #- Implemented a beter version of the gernalized view.  It stores an empty
    #  which has axes aligned with the insertion axis of the prep as defined by
    #  the new "define view" function.
    #- New function "go to view" reset the master model to be aligned with prep
    #  insertino axis.  This applies the master model rotation so there is some
    #  worry that this could affecct some of the parenting and other directionally
    #  dependent modifiers (eg, projection!) So it will be important to apply those
    #  before going to other steps.  Unsure on the full extent of this implementation
    #  on other functions but a first pass edit has hopefully eliminated most of the
    #  inconsitencies
    
    
## Changes in Rev 1.0.1 10/19/2011
    #- Added functionality to automatically enable dependencies (looptools, bsurfaces, relax)
    #- Tweaked the simple coping function becuase it was not working with some
    #  the new methods for keeping track of the different objects in the scene.
    
#January Changes
    #  Major problems with parenting and matrix math...starting to fix. 2.61a
    
################################################################################
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

def get_com(me,verts,mx):
    from mathutils import Vector, Matrix
    '''
    args:
        me - the Blender Mesh data
        verts- a list of indices to be included in the calc
        mx- thw world matrix of the object, if empty assumes unity
        
    '''
    if not mx:
        mx = Matrix()
    COM = Vector((0,0,0))
    l = len(verts)
    for v in verts:
        COM = COM + me.vertices[v].co
        
    COM = mx  * (COM/l)
    
    return COM


def extrude_edges_in(me, edges, mx, res):
    from mathutils import Vector, Matrix
    from bpy_extras.mesh_utils import edge_loops_from_edges
    '''
    args:
        me - Blender Mesh Data
        edges - edges (not indices of edges)
        mx  - world matrix
        res - distance step for each extrusion
    '''
    
    z = Vector((0,0,1))
    if not mx:
        mx = Matrix()
    
    verts_in_order = edge_loops_from_edges(me,edges)
    verts_in_order = verts_in_order[0]
       
    verts_in_order.append(verts_in_order[1])
    l = len(verts_in_order)    
    verts_alone = verts_in_order[0:l-2]
    
    
    lerps = []
    curl = 0
    
    for n in range(0,l-2):
        a = verts_in_order[n]
        b = verts_in_order[n+1]
        c = verts_in_order[n+2]
        v0 = me.vertices[a]
        v1 = me.vertices[b]
        v2 = me.vertices[c]
        
        #Vec representation of the two edges
        V0 = mx * (v1.co - v0.co)
        V1 = mx * (v2.co - v1.co)
        
        ##XY projection
        temp0 = Vector((V0[0],V0[1],0))
        temp1 = Vector((V1[0],V1[1],0))
        
        cross0 = temp0.cross(temp1)
        
        sign = 1
        if cross0[2] < 0:
            sign = -1
        
        rot = temp0.rotation_difference(temp1)  
        ang = rot.angle
    
        curl = curl + ang*sign
        lerps.append(V0.lerp(V1,.5))
        
    clockwise = 1

    if curl < 0:
        clockwise = -1
    print(curl)
    
    
    bpy.ops.object.mode_set(mode = 'EDIT')
    bpy.ops.mesh.select_all(action = 'DESELECT')
    bpy.ops.object.mode_set(mode = 'OBJECT')
        
    for n in range(0,l-2):
        #ignore this stuff, its for other things.
        #a = verts_in_order[n]
        b = verts_in_order[n+1]
        #c = verts_in_order[n+2]
        #v0 = me.vertices[a]
        v1 = me.vertices[b]
        #v2 = me.vertices[c]

    
        V = lerps[n]
        Trans = z.cross(V)*clockwise
        Trans.normalize()
    
        v1.select = True
        bpy.ops.object.editmode_toggle()
        bpy.ops.transform.translate(value = Trans*res)
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.editmode_toggle()
        
    for v in verts_alone:
        me.vertices[v].select = True
        
    bpy.ops.object.mode_set(mode='EDIT')
        
def fill_loop_scale(ob, edges, res):
    from math import ceil
    from mathutils import Vector, Matrix
    from bpy_extras.mesh_utils import edge_loops_from_edges
    '''
    args:
        ob - Blender Object (must be mesh)
        edges - edges which constitute the loop (not indices of edges)
        mx  - world matrix
        res - appprox size of step (optional)
    
        
    '''
    if not ob:
        ob = bpy.context.object
    
    me = ob.data
    mx = ob.matrix_world
        
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode = 'OBJECT')
    bpy.ops.object.select_all(action = 'DESELECT')
    
    ob.hide = False
    ob.select = True
    bpy.context.scene.objects.active = ob
    
    
    verts = edge_loops_from_edges(me,edges)
    verts = verts[0]
    verts.pop()
    
    n=len(ob.vertex_groups)
    bpy.ops.object.vertex_group_add()
    bpy.context.object.vertex_groups[n].name='filled_hole'
    
    
    n=len(ob.vertex_groups)
    bpy.context.tool_settings.vertex_group_weight = 1
    bpy.ops.object.vertex_group_add()
    bpy.context.object.vertex_groups[n].name='original_verts'
    
    
    #notice now that ob.vertex_groups[n-1] is original_verts
    #and ob.vertex_groups[n-2] = filled_hole
    
    bpy.context.tool_settings.mesh_select_mode = [True, False, False]
    bpy.ops.object.mode_set(mode = 'EDIT')
    
    bpy.ops.mesh.select_all(action = 'SELECT')
    bpy.ops.object.vertex_group_assign()
    bpy.ops.mesh.select_all(action = 'DESELECT')
    
    
    bpy.ops.object.mode_set(mode = 'OBJECT')
    for v in verts:
        me.vertices[v].select = True
    bpy.ops.object.mode_set(mode = 'EDIT')
    
    #### Now we are ready to actually do something  ###
    
    #find COM of selected verts
    COM = get_com(me,verts,mx)
    print('global COM is')
    print(COM)
    #calc the average "radius" of the loop
    
    R=0
    L = len(verts)
    for v in verts:
        r = mx * me.vertices[v].co - COM     
        R = R + r.length

    R = R/L
    print('the average radius is')
    print(R)
    
    if not res:
        lengths=[]
        vert_loop = verts[:]
        vert_loop.append(verts[0])
        
        l = len(vert_loop)
        for i in range(0,l-1):
            a = vert_loop[i]
            b = vert_loop[i+1]
            v0=mx * me.vertices[a].co
            v1=mx * me.vertices[b].co
            V=v1-v0
          
            lengths.append(V.length)
    
        res=min(lengths)
        print('taking min edge length as res')
        print(res)

    step = ceil(R/res)
    print(step)
    
    bpy.ops.object.vertex_group_set_active(group = 'filled_hole')
    scl = 1

    for i in range(1,step):
    
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
    
        me = ob.data
        sverts=len([v for v in me.vertices if v.select])
    
        if sverts > 4:
            print('extruding again')
            bpy.ops.mesh.extrude_edges_move()
            bpy.ops.object.vertex_group_assign()
            scl = (1 - 1/step*i)/scl
   
    
            bpy.ops.transform.resize(value = (scl, scl, scl))    
            bpy.ops.mesh.remove_doubles(mergedist=.85*res)    
            bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='3', regular=True)
        
        
        if sverts < 3:
            print('break at <3')
            break
                
        if (sverts <= 4 and sverts > 2) or i == step -1:
            print('break at 3 and fill remainder')
            bpy.ops.mesh.fill()
            bpy.ops.mesh.vertices_smooth(repeat =3)
            bpy.ops.object.vertex_group_assign()
            break
        
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
    
    print("update my test function")
    sce = bpy.context.scene
    
    #gather all the relevant active and selected things       
    if bpy.context.object:
        ob_now = bpy.context.object
        hide_now = ob_now.hide
        mode_now = bpy.context.object.mode
        ob_now.hide = False
    else:
        ob_now = None
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
    for ob in sce.objects:
        ob.select = False
        
    if ob_now:
        sce.objects.active = ob_now
        ob_now.select = True
        ob_now.hide = hide_now
    for ob in sel_now:
        ob.select = True
    
    if bpy.context.mode != mode_now:           
        bpy.ops.object.mode_set(mode = mode_now)

##########################################
####### Custom Properties ################
##########################################

class WorkingTeeth(bpy.types.PropertyGroup):
    

    name = bpy.props.StringProperty(name="Tooth Number",default="Unknown")
    axis = bpy.props.StringProperty(name="Insertion Axis",default="")
    mesial = bpy.props.StringProperty(name="Distal Model",default="")
    distal = bpy.props.StringProperty(name="Distal Model",default="")
    prep_model = bpy.props.StringProperty(name="Prep Model",default="")
    margin = bpy.props.StringProperty(name="Margin",default="")
    pmargin = bpy.props.StringProperty(name="PsMargin",default="")
    bubble = bpy.props.StringProperty(name="Bubble",default="")
    restoration = bpy.props.StringProperty(name="Restoration",default="")
    contour = bpy.props.StringProperty(name="Full Contour",default="")
    coping = bpy.props.StringProperty(name="Simple Coping",default="")
    acoping = bpy.props.StringProperty(name="Anatomic Coping",default="")
    inside = bpy.props.StringProperty(name="Inside",default="")
    in_bridge = bpy.props.BoolProperty(name="Incude in Bridge", default=False)
    
    
    rest_types=['CONTOUR',
                'PONTIC',
                'COPING',
                'ANATOMIC COPING']
    rest_enum = []
    for index, type in enumerate(rest_types):
        rest_enum.append((str(index), rest_types[index], str(index)))
        
    rest_type = bpy.props.EnumProperty(
        name="Restoration Type", 
        description="The type of restoration for this tooth", 
        items=rest_enum, 
        default='0',
        options={'ANIMATABLE'})
    
bpy.utils.register_class(WorkingTeeth)

bpy.types.Scene.working_teeth = bpy.props.CollectionProperty(type=WorkingTeeth, name = "Working Teeth")
bpy.types.Scene.working_tooth_index = bpy.props.IntProperty(name = "Working Tooth Index", min=0, default=0, update=update_func)




##########################################
#######      Operators    ################
##########################################

################################################################################ 

class  AddDentalParameters(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.add_dental_parameters'
    bl_label = "Add Dental Parameters"

    def execute(self, context):
        sce=bpy.context.scene
        
        #check for the existing properties
        eprops = [prop.name for prop in bpy.types.Scene.bl_rna.properties]
        
        if "Master Model" not in eprops:
            bpy.types.Scene.master_model = bpy.props.StringProperty(
                name="Master Model",
                default="")
        if "Opposing Model" not in eprops:
            bpy.types.Scene.opposing_model = bpy.props.StringProperty(
                name="Opposing Model",
                default="")
                
        bpy.types.Scene.cement_gap = bpy.props.FloatProperty(
            name="Default Cement Gap",
            default=.07)
        bpy.types.Scene.i_contact = bpy.props.FloatProperty(
            name="Def IP Contact",
            default=.025)
        bpy.types.Scene.o_contact = bpy.props.FloatProperty(
            name="Default Occlusal Contact",
            default=.025)            
        bpy.types.Scene.holy_zone = bpy.props.FloatProperty(
            name="Default Holy Zone Width",
            default=.5)            
        bpy.types.Scene.thickness = bpy.props.FloatProperty(
            name="Default Min Thickness",
            default=.75)
        bpy.types.Scene.coping_thick = bpy.props.FloatProperty(
            name="Default Coping Thickness",
            default=.45)
        
        margin_methods = ['MANUAL', 'PROJECTION', 'WALKING']
        marg_enum = []
        for index, type in enumerate(margin_methods):
            marg_enum.append((str(index), margin_methods[index], str(index)))
         
        bpy.types.Scene.margin_method = bpy.props.EnumProperty(
            name="Margin Method",
            description="The way the margin is marked",
            items=marg_enum,
            default='0')
            
            
        design_stages =['0.ALL',
                        '1.BULK PROCESSING',
                        '2.SEGMENTATION',
                        '3.MARGIN MARKING',
                        '4.RESTORATION DESIGN',
                        '5.FINALIZATION',
                        'EXPERIMENTAL']
        stages_enum = []
        for index, type in enumerate(design_stages):
            stages_enum.append((str(index), design_stages[index], str(index)))
         
        bpy.types.Scene.design_stage = bpy.props.EnumProperty(
            name="Design Stage",
            description="Stage of design process",
            items=stages_enum,
            default='0')

        bpy.types.Scene.dynamic_oc = bpy.props.BoolProperty("Dyn. Occlusion")
        bpy.types.Scene.dynamic_ipm = bpy.props.BoolProperty("Dyn. Mesial")
        bpy.types.Scene.dynamic_ipd = bpy.props.BoolProperty("Dyn. Distal")
        bpy.types.Scene.dynamic_margin = bpy.props.BoolProperty("Dyn. Margin")

        bpy.types.Scene.all_functions = bpy.props.BoolProperty("Show All Functions")
        
        return {'FINISHED'}

class  AddDentalMaterials(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.add_dental_materials'
    bl_label = "Add Dental Materials"

    def execute(self, context):
        
        if 'intaglio_material' not in bpy.data.materials:
            
            bpy.data.materials.new(name = 'intaglio_material')
            mat = bpy.data.materials["intaglio_material"]
            mat.diffuse_color = Color((.687,.01,.04))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if 'prep_material' not in bpy.data.materials:
                       
            bpy.data.materials.new(name = 'prep_material')
            mat = bpy.data.materials["prep_material"]
            mat.diffuse_color = Color((1,.9,.5))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if 'opposing_material' not in bpy.data.materials:

            bpy.data.materials.new(name = 'opposing_material')
            mat = bpy.data.materials["opposing_material"]
            mat.diffuse_color = Color((.2,.7,.2))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if 'restoration_material' not in bpy.data.materials:
                        
            bpy.data.materials.new(name = 'restoration_material')
            mat = bpy.data.materials["restoration_material"]
            mat.diffuse_color = Color((1,.94,.9))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if 'connector_material' not in bpy.data.materials:
            
            bpy.data.materials.new(name = 'connector_material')
            mat = bpy.data.materials["connector_material"]
            mat.diffuse_color = Color((.6,.02,.34))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
            
        if 'master_material' not in bpy.data.materials:
            
            bpy.data.materials.new(name = 'master_material')
            mat = bpy.data.materials["master_material"]
            mat.diffuse_color = Color((.6,.02,.34))
            mat.use_transparency = True
            mat.alpha = .5
            mat.use_fake_user = True
        
        return {'FINISHED'}


class SetMaster(bpy.types.Operator):
    ''''''
    bl_idname='view3d.set_master'
    bl_label="Set Master"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):        
        
        if len(bpy.context.selected_editable_objects) > 1:
            bpy.ops.object.join()
        
        ob=bpy.context.object
        
        n = 5
        if len(ob.name) < 5:
            n = len(ob.name) - 1
        
        new_name = "Master_" + ob.name[0:n]
        ob.name = new_name
        
        bpy.context.scene.master_model = new_name       
        
        return{'FINISHED'}
    
class SelectArea(bpy.types.Operator):
    ''''''
    bl_idname='view3d.select_area'
    bl_label="Select Area"
    
    def execute(self, context):
    
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.context.tool_settings.use_snap = False
        bpy.context.tool_settings.proportional_edit = 'DISABLED'        
        bpy.context.space_data.use_occlude_geometry = False          
        
        return{'FINISHED'}
       

class SetOpposing(bpy.types.Operator):
    ''''''
    bl_idname='view3d.set_opposing'
    bl_label="Set Opposing"
    
    def execute(self, context):
    
        ob=bpy.context.object
        n = 5
        if len(ob.name) < 5:
            n = len(ob.name) - 1
        
        new_name = 'Opposing_' + ob.name[0:n]
        ob.name = new_name
        bpy.context.scene.opposing_model = new_name      
        
        return{'FINISHED'} 
            

class AppendWorkingTooth(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.append_working_tooth'
    bl_label = "Append Working Tooth"
    bl_options = {'REGISTER','UNDO'}
    
    #We will select a tooth to work on
    teeth = [11,12,13,14,15,16,17,18,21,22,23,24,25,26,27,28,31,32,33,34,35,36,37,38,41,42,43,44,45,46,47,48]    
    teeth_enum=[]
    for index, o in enumerate(teeth):
        teeth_enum.append((str(index), str(o), str(index))) 
    ob_list = bpy.props.EnumProperty(name="Tooth to work on", description="A list of all teeth to chose from", items=teeth_enum, default='0')
    
    #We will also select a type of restoration
    rest_types=['CONTOUR',
                'PONTIC',
                'COPING',
                'ANATOMIC COPING']
    rest_enum = []
    for index, type in enumerate(rest_types):
        rest_enum.append((str(index), rest_types[index], str(index)))
    rest_type = bpy.props.EnumProperty(name="Restoration Type", description="The type of restoration for this tooth", items=rest_enum, default='0')
    
    in_bridge = bpy.props.BoolProperty(name="Incude in Bridge", default = False)
    
    
    #abutment = bpy.props.BoolProperty(name="Abutment", description="If Pontic Uncheck", default = True)   
    
    def invoke(self, context, event): 
        
        #context.window_manager.invoke_search_popup(self)
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
    
    def execute(self, context):

        my_item = bpy.context.scene.working_teeth.add()
        indx = int(self.properties.ob_list)
        
        print(indx)
        
        
        my_item.name = str(self.teeth[int(self.properties.ob_list)])
        #my_item.abutment = self.properties.abutment
        
        my_item.rest_type = self.properties.rest_type
        
        my_item.in_bridge = self.properties.in_bridge
        
        return {'FINISHED'}
    
    #def draw(self, context):
        
        #layout = self.layout
        #box = layout.box()
        #box.label("Choose A Tooth")
        #box.prop(self, "ob_list")
        
        #box.label("Abutment?")
        #box.prop(self, "abutment")

class RemoveWorkingTooth(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.remove_working_tooth'
    bl_label = "Remove Working Tooth"
    

    
    def execute(self, context):

        j = bpy.context.scene.working_tooth_index
        bpy.context.scene.working_teeth.remove(j)
        
        
        return {'FINISHED'}
 
class CursorToBound(bpy.types.Operator):
    '''Tooltip'''
    bl_idname = "object.cursor_to_bound"
    bl_label = "Cursor to Bound"
    bl_options = {'REGISTER','UNDO'}

    xyz = bpy.props.BoolVectorProperty(name = "xyz", default = (False,False,False))
    negative = bpy.props.BoolVectorProperty(name = "pos/neg", default = (True,True,True))

    def execute(self, context):
        
        #construct the correct matrix
        xyz = Matrix()
        xyz = xyz.to_3x3()
        
        for i in range(0,3):
            for j in range(0,3):
                if i == j:
                    if not self.negative[i]:
                        neg = -1
                    else:
                        neg = 1
                    print(neg)
                    print(self.xyz[i])   
                    xyz[i][j] = self.xyz[i]*neg
        

        print(xyz)
        sce = bpy.context.scene
        ob = bpy.context.object
        
        b_box  = ob.bound_box
        mx = ob.matrix_world
        dim = ob.dimensions
        
        #calc bbox_center
        b_cent = Vector((0,0,0))
        for corner in b_box:
            b_cent = b_cent + mx * Vector(list(corner))
    
        b_cent =  1/8 * b_cent

        cursor = b_cent + xyz * dim/2

        sce.cursor_location = cursor
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
    
        
class ProcessModels(bpy.types.Operator):

    ''''''
    bl_idname = 'view3d.process_models'
    bl_label = "Process Models"
    bl_options = {'REGISTER','UNDO'}   
    
    """ 
    This groups all the objects in the scene under the master modelsuch that
    all objects will move relative to it.  It also sets up the various colors 
    for your objects to make them easier tovisualize
    
    """

    transparent = bpy.props.BoolProperty(name="Make Transparent?", default=False)
    def execute(self, context):
        
        sce=bpy.context.scene
        bpy.ops.object.select_all(action = 'DESELECT')
        
################################################################################
#################### 80 Character PEP 8 Style Guide  ###########################


        #The first thing this functino does is check to see if the appropriate
        #materials are in place.  These materials are customizable and serve as
        #visual cues to help the operator know what they are looking at.  This
        #coul be taken care of in an automatic function (@ registration?) but
        #because this is a mandatory step, and the first step which uses materials
        #this is where I chose to put it in place.        
        
        #Get the materials
        mat1=bpy.data.materials["prep_material"]
        mat2=bpy.data.materials["opposing_material"]
        
        #Get the master model
        master=sce.master_model
        Master=sce.objects[master]
        
        #Assing the material to it's data    
        me1=Master.data
        me1.materials.append(mat1)
        if self.transparent:
            Master.show_transparent = True
        
        #Do the same for the opposing model if there is one.
        if sce.opposing_model:
            opposing=sce.opposing_model
            Opposing=sce.objects[opposing]
            me2=Opposing.data
            me2.materials.append(mat2)
            Opposing.show_transparent = True        
            
        
        for A in bpy.context.window.screen.areas:
            if A.type == 'VIEW_3D':
                for s in A.spaces:
                    if s.type == 'VIEW_3D':
                        s.pivot_point = 'CURSOR'
        ##########Old Way################
        #Just parent the opposing to the master model
        #bpy.ops.object.select_all(action='DESELECT')
        #Master.select = True
        #Opposing.select = True
        
        #bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
        #sce.objects.active=Master
        #bpy.ops.object.parent_set()    
        
        #Opposing.select = False
        #################################
        
        
################################################################################
#################### 80 Character PEP 8 Style Guide  ###########################
        
        ########New Way###############
        #parent everything to the master model.  In some situations, scan data
        #will come in different formats. Sometimes we need to manually segment
        #out pieces and other times, the models are individuals.  In any case,
        # this is the safest way to make sure the spatial relationship is
        #preserved.  If user has other objects in the sceen, they will get
        #parented as well which can be risky.  In 99% of cases, there should be
        #no other objects in this scene.
        
             
        for ob in sce.objects:
            if ob.name != master:
                ob.hide = False
                ob.select = True
                if ob.name != sce.opposing_model:
                    dat = ob.data
                    dat.materials.append(mat1)
        
        sce.objects.active=Master
        bpy.ops.object.parent_set(type='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        Master.select = True
        
        for ob in sce.objects:
            if ob.name != master:
                ob.hide = True       
        bpy.ops.view3d.snap_cursor_to_center()
        #T=bpy.context.object.location*-1
        #bpy.ops.transform.translate(value=T)
        
        
        
        bpy.ops.view3d.viewnumpad(type='TOP')
        
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.editmode_toggle()
        
        ###
        #At the end
        
        return {'FINISHED'}
    
    
class GoToAxis(bpy.types.Operator):

    ''''''
    bl_idname = 'view3d.go_to_axis'
    bl_label = "Go To Axis"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):

        sce = bpy.context.scene
        master=sce.master_model
        
        
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        prep = tooth.prep_model
        axis = tooth.axis
        if not master or not axis:
            self.report('WARNING', "Whoops! There is either no master model or no set axis for this restoration")
            return{'CANCELLED'}
        
        #align the view to the empty
        Empty = sce.objects[axis]
        mx = Empty.matrix_world
        rot = mx.to_quaternion()
        irot = rot.inverted()

        Master=sce.objects[master]
        Master.show_transparent = False        
        bpy.context.scene.objects.active = Master
        Master.select = True
        
        v3d = bpy.context.space_data
        v3d.pivot_point = 'CURSOR'
        
        sce.cursor_location = Master.location
        
        bpy.ops.object.transform_apply(rotation=True)
        Master.rotation_mode = 'QUATERNION'
        
        Master.rotation_quaternion = irot        
        bpy.ops.object.transform_apply(rotation = True)
        bpy.ops.view3d.viewnumpad(type = "TOP")
         
        return {'FINISHED'}
    
    
class DefineAxis(bpy.types.Operator):

    ''''''
    bl_idname = 'view3d.define_axis'
    bl_label = "Define Axis"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):

        sce = bpy.context.scene        
        master=sce.master_model        
        
        
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        prep = tooth.prep_model
        axis = tooth.axis
        a = tooth.name
       
        #check to make sure the master model is set
        if not master:
            self.report('WARNING', "There is no master model.  Please define one first")
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
            tooth.axis = ''
            
        
        #Add a new one
        current_objects=list(bpy.data.objects)
        bpy.ops.object.add(type = 'EMPTY')
        for o in bpy.data.objects:
            if o not in current_objects:
                Empty = o
                o.name = str(a + '_Axis')
                tooth.axis = o.name

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
        
        if prep:
            bpy.ops.object.select_all(action = 'DESELECT')
            Prep = sce.objects[prep]
            Prep.hide = False
            Prep.select = True
            sce.objects.active = Prep
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
            
         
        return {'FINISHED'}  

class ViewToZ(bpy.types.Operator):
    '''Aligns the local coordinates of the acive object with the view'''
    bl_idname = "view3d.view_to_z"
    bl_label = "View to Z"
    bl_options = {'REGISTER','UNDO'}

    keep_orientation = bpy.props.BoolProperty(default = False, name = "Keep Orientation")
    
    def execute(self, context):
        bpy.ops.object.select_all(action = 'DESELECT')
        ob = bpy.context.object
        ob.select = True
        
        #necessary because I don't want to have to wory
        #about what the transform orientation might be
        bpy.ops.object.transform_apply(rotation = True)
        
        #this is what the view rotation is reported as
        #so for convenience I will just make the object
        #use it
        ob.rotation_mode = 'QUATERNION'
        
        #gather info
        space = bpy.context.space_data
        region = space.region_3d        
        vrot = region.view_rotation       
        align = vrot.inverted()
               
        #rotate the object the inverse of the view rotation
        ob.rotation_quaternion = align
        
        #if we want to keep the rotatio nof the object in
        #the scene and essentially just set the object's
        #local coordinates to the view...then do this.      
        if self.keep_orientation:
            bpy.ops.object.transform_apply(rotation = True)
            ob.rotation_quaternion = vrot   
            return ('FINISHED')
                
        return {'FINISHED'}
    
class TossOthers(bpy.types.Operator):
    
    ''''''
    bl_idname='object.toss_others'
    bl_label="Toss Others"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        
        bpy.ops.object.select_all(action="INVERT")
        bpy.ops.object.delete()
        
        
        return {'FINISHED'}   

    
class SplitData(bpy.types.Operator):
    
    ''''''
    bl_idname='view3d.split_data'
    bl_label="Split Data"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        
        #context....one object selected
        
        sce = bpy.context.scene
        if bpy.context.mode == 'OBJECT':
            
            for ob in sce.objects:
                if ob.select:
                    sce.objects.active = ob
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode='OBJECT')
            
        if bpy.context.mode == 'EDIT':
            
            
            current_objects=list(bpy.data.objects)
        
        
            bpy.ops.mesh.duplicate()
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.editmode_toggle()
        
            new_objects=[]
            for o in bpy.data.objects:
                if o not in current_objects:
                    new_objects.append(o)
                
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.scene.objects.active=new_objects[0]
        
        return {'FINISHED'}

class DefineDistal(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.define_distal'
    bl_label = "Define Distal"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        
        sce = bpy.context.scene
        
        master=sce.master_model
        Master=sce.objects[master]
        current_objects=list(bpy.data.objects)
        
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        dis=str(a + "_Distal")
        
        if bpy.context.mode == 'OBJECT':
            
            ob = bpy.context.object
            tooth.distal = ob.name
            
        if bpy.context.mode == 'EDIT_MESH':
            
            bpy.ops.mesh.duplicate()
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.editmode_toggle()
        
            new_objects=[]
            for o in bpy.data.objects:
                if o not in current_objects:
                    new_objects.append(o)
        
        
            bpy.ops.object.select_all(action='DESELECT')
            new_objects[0].name=dis
            new_objects[0].show_bounds=True
        
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.scene.objects.active=new_objects[0]
            new_objects[0].select=True
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
            tooth.distal = dis
            
            bpy.context.scene.objects.active=Master           
            bpy.ops.object.parent_set(type='OBJECT')
            
                    
            bpy.ops.object.editmode_toggle()        
        
        
            bpy.ops.view3d.viewnumpad(type='TOP')
            bpy.ops.mesh.select_all(action='DESELECT')        

        return {'FINISHED'}


class DefineMesial(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.define_mesial'
    bl_label = "Define Mesial"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        
        master=bpy.context.scene.master_model
        Master=bpy.context.scene.objects[master]
        current_objects=list(bpy.data.objects)
        
        sce = bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        mes=str(a + "_Mesial")
        
        if bpy.context.mode == 'OBJECT':
            
            ob = bpy.context.object
            tooth.mesial = ob.name
            
        if bpy.context.mode == 'EDIT_MESH':
            bpy.ops.mesh.duplicate()
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.editmode_toggle()
        
            new_objects=[]
            for o in bpy.data.objects:
                if o not in current_objects:
                    new_objects.append(o)
        
        
            bpy.ops.object.select_all(action='DESELECT')
            new_objects[0].name=mes            
            new_objects[0].show_bounds=True
        
            bpy.ops.object.select_all(action='DESELECT')
            
            sce.objects.active=new_objects[0]
            new_objects[0].select=True        
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
            
            sce.objects.active=Master
            bpy.ops.object.parent_set(type='OBJECT')
       
            tooth.mesial = mes
            bpy.ops.object.editmode_toggle()
        
            bpy.ops.view3d.viewnumpad(type='TOP')
            bpy.ops.mesh.select_all(action='DESELECT')        

        return {'FINISHED'}

    
    

class SetAsPrep(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.set_as_prep'
    bl_label = "Set as Prep"
    bl_options = {'REGISTER','UNDO'}
    
    abutment = bpy.props.BoolProperty(name = "abutment", default = False)
    
    def execute(self, context):
        
        sce=bpy.context.scene
        
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name

        prep = str( a + "_Prep")
        
        master=bpy.context.scene.master_model
        Master=bpy.context.scene.objects[master]
        current_objects=list(bpy.data.objects)
        
        if bpy.context.mode == 'OBJECT':
            
            ob = bpy.context.object
            if ob.name != sce.master_model:
                ob.name = prep
                tooth.prep_model = ob.name
                Prep = ob
                
            if ob.name == master:
                current_objects = list(sce.objects)
                bpy.ops.object.duplicate()                
                new_objs = []
                for ob in sce.objects:
                    if ob not in current_objects:                        
                        new_objs.append(ob)
                Prep = new_objs[0]               
                Prep.name = prep
                
            Prep.select = True
            sce.objects.active = Master
            
            bpy.ops.object.parent_set(type='OBJECT')
            
            sce.objects.active = Prep
            
            #this will prevent us from messing up any 
            #abutment/implant relationships. So that we can
            #adjust implant placement after consideration of
            #restorative solution.
            if not self.abutment:
                sce.objects.active = Master
                Prep.select = True
                bpy.ops.object.parent_set(type = 'OBJECT')     
            
            Master.hide = True
        
            bpy.ops.view3d.viewnumpad(type='TOP')
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')                
            tooth.prep_model = prep    
            
        if bpy.context.mode == 'EDIT_MESH':    
            bpy.ops.mesh.duplicate()
            bpy.ops.mesh.separate(type='SELECTED')
            bpy.ops.object.editmode_toggle()
        
            new_objects=[]
            for o in bpy.data.objects:
                if o not in current_objects:
                    new_objects.append(o)
        
        
            bpy.ops.object.select_all(action='DESELECT')
            new_objects[0].name= prep
            tooth.prep_model = prep
            Prep=bpy.data.objects[prep]
            Prep.select = True
            sce.objects.active = Master
            bpy.ops.object.parent_set(type='OBJECT')
            
            Master.hide = True
        
            bpy.ops.view3d.viewnumpad(type='TOP')
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
            
            bpy.ops.object.select_all(action = 'DESELECT')
     
        Prep.layers[1] = True
        return {'FINISHED'}

class SetAsIntaglio(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.set_intaglio'
    bl_label = "Set as Intaglio"
    
    
    def execute(self, context):
        bpy.context.tool_settings.vertex_group_weight = 1
        master=bpy.context.scene.master_model
        Master=bpy.context.scene.objects[master]
        
        sce=bpy.context.scene
        j = bpy.context.scene.working_tooth_index
        a = bpy.context.scene.working_teeth[j].name
        prep = str(a + "_Prep")
        
        #need to add some if statements to make sure everything is in order for this step
        #also, neeed to add an option for auto intaglio based on some width or some number
        #of edge loops when the crown inside is calculated.
        
        Prep = bpy.data.objects[prep]
        n=len(Prep.vertex_groups)
        bpy.ops.object.vertex_group_assign(new=True)
        bpy.context.object.vertex_groups[n].name='intaglio'
        
        
        i=len(Prep.modifiers)
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = Prep.modifiers[i]
        mod.target=bpy.context.scene.objects[master]
        mod.offset=bpy.context.scene.i_contact
        mod.use_keep_above_surface=True
        mod.vertex_group='intaglio'
        
        j=len(Prep.material_slots)
        bpy.ops.object.material_slot_add()
        Prep.material_slots[j].material=bpy.data.materials["intaglio_material"]
        bpy.ops.object.material_slot_assign()
        bpy.ops.object.editmode_toggle()
        bpy.data.objects[prep].select=True
        bpy.ops.view3d.snap_cursor_to_active()
        
        Prep.parent=Master
        return {'FINISHED'}


class MarginFromView(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.margin_from_view'
    bl_label = "Margin From View"
    bl_options = {'REGISTER','UNDO'}
    

    
    def execute(self, context):
        
        sce = bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        prep = tooth.prep_model
        Prep = sce.objects[prep]
        master = sce.master_model
        Master = sce.objects[master]
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
        
        for o in sce.objects:
            if o.name != prep and not o.hide:
                o.hide = True
                
        for A in bpy.context.window.screen.areas:
            if A.type == 'VIEW_3D':
                for s in A.spaces:
                    if s.type == 'VIEW_3D':
                        s.pivot_point = 'MEDIAN_POINT'        
        #Copy the prep data so we can collapse it to approximate
        #the outline of it.
        
        Prep.hide = False
        Prep.select = True
        sce.objects.active = Prep
        ob = Prep.copy()
        new_data = ob.data.copy()
        new_data.name = 'temp_prep'
        ob.name = 'temp_prep'
        ob.data = new_data
        
        ob.data.user_clear
        sce.objects.link(ob)
        
        #Get access to the objects mesh
        bpy.ops.object.select_all(action = 'DESELECT')
        TempPrep = sce.objects['temp_prep']
        sce.objects.active = TempPrep
        TempPrep.select = True
        
        bpy.ops.object.transform_apply(rotation = True, scale = True)
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')        
        bpy.ops.transform.resize(value = (1,1,0))
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        #hold on to the maximum size of the object
        dim = max(ob.dimensions)
        bpy.ops.object.origin_set(type = 'ORIGIN_GEOMETRY')        
        bpy.ops.view3d.snap_cursor_to_selected()
        loc = sce.cursor_location
        
        bpy.ops.mesh.primitive_circle_add(vertices = 16, radius = 1.3*dim/2, location = loc)
        
        Margin = bpy.context.object  #this is the circle we just added
        Margin.name = str(a + '_Margin')
        Margin.parent = Master
        tooth.margin = Margin.name
        
        n = len(Margin.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Margin.modifiers[n]
        mod.target = TempPrep
        
        bpy.ops.object.modifier_copy(modifier = 'SHRINKWRAP')
        bpy.ops.object.modifier_apply(modifier = 'SHRINKWRAP')
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.subdivide(number_cuts = 1)              
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        #bpy.ops.object.modifier_copy(modifier = Margin.modifiers[0].name)        
        bpy.ops.object.modifier_apply(modifier = Margin.modifiers[0].name)
        
        #bpy.ops.object.mode_set(mode = 'EDIT')
        #bpy.ops.mesh.select_all(action = 'SELECT')
        #bpy.ops.mesh.subdivide(number_cuts = 1)              
        #bpy.ops.object.mode_set(mode = 'OBJECT')
        
        #bpy.ops.object.modifier_apply(modifier = Margin.modifiers[0].name)
        
               
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.vertices_sort()
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.transform_apply(location = True) #this is necessary for my extrude edges in script to work blah
        me = Margin.data
        sel_edges = Margin.data.edges
        mx = Margin.matrix_world        
        extrude_edges_in(me, sel_edges, mx, .1)
        
        n = len(Margin.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Margin.modifiers[n]
        mod.wrap_method = 'PROJECT'
        mod.use_project_z = True
        mod.use_negative_direction = True
        mod.use_positive_direction = False
        mod.target = Prep
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
             
        bpy.ops.object.modifier_apply(modifier = Margin.modifiers[0].name)
        
        sce.tool_settings.use_snap = True
        sce.tool_settings.snap_element = 'FACE'
        sce.tool_settings.snap_target = 'ACTIVE'        
        
        n = len(Margin.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Margin.modifiers[n]
        mod.target = Prep
        mod.show_in_editmode = True
        mod.show_on_cage = True
        
        n = len(Margin.modifiers)
        bpy.ops.object.modifier_add(type = 'SUBSURF')
        mod = Margin.modifiers[n]
        mod.subdivision_type = 'SIMPLE'
        mod.levels = 3       
        
        n = len(Margin.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Margin.modifiers[n]
        mod.target = Prep
        
        bpy.ops.transform.resize(value = (1.1, 1.1, 1))
        
        
        bpy.ops.object.select_all(action = 'DESELECT')
        TempPrep.select = True
        sce.objects.active = TempPrep
        bpy.ops.object.delete()
        
        Margin.select = True
        sce.objects.active = Margin
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        
        
        return {'FINISHED'}
    
class InitiateMargin(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.initiate_margin'
    bl_label = "Initiate Margin"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        
        
        sce=bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        prep = tooth.prep_model
        margin = str(a + "_Margin")
        
        Prep = bpy.data.objects[prep]
        Prep.hide = False
        L = Prep.location
        #L = bpy.context.scene.cursor_location
        
        
        ###Keep a list of unhidden objects
        
        for o in sce.objects:
            if o.name != prep and not o.hide:
                o.hide = True
        
        master=sce.master_model
        Master = bpy.data.objects[master]
        
        bpy.ops.view3d.viewnumpad(type='TOP')
        bpy.ops.object.select_all(action='DESELECT')
        #bpy.context.scene.cursor_location = L
        bpy.ops.curve.primitive_bezier_curve_add(view_align=True, enter_editmode=True, location=L)
        bpy.context.tool_settings.use_snap = True
        bpy.context.tool_settings.snap_target= 'ACTIVE'
        bpy.context.tool_settings.snap_element = 'FACE'
        bpy.context.tool_settings.proportional_edit = 'DISABLED'
        o=bpy.context.object
        o.name=margin
        o.parent=Master #maybe this should go in the "Accept Margin" function/step
        bpy.ops.curve.handle_type_set(type='AUTOMATIC')
        bpy.ops.curve.select_all(action='DESELECT')
        bpy.context.object.data.splines[0].bezier_points[1].select_control_point=True
        bpy.ops.curve.delete()
        bpy.ops.curve.select_all(action='SELECT')
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = bpy.context.object.modifiers[0]
        #target has been changed to master to allow for margin initiated prep segmentation
        mod.target=Prep
    
        tooth.margin = margin
        return {'FINISHED'}

class InitiateAutoMargin(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.initiate_auto_margin'
    bl_label = "Initiate Auto Margin"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        
        
        sce=bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        prep = tooth.prep_model
        margin = str(a + "_Margin")
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
        Prep = bpy.data.objects[prep]
        Prep.hide = False
        Prep.show_transparent = False
        
        bpy.ops.object.select_all(action='DESELECT')
        Prep.select = True
        sce.objects.active = Prep
        
        prep_cent = Vector((0,0,0))
        for v in Prep.bound_box:
            prep_cent = prep_cent + Prep.matrix_world * Vector(v)
        Prep_Center = prep_cent/8
        
        sce.cursor_location = Prep_Center     
        ###Keep a list of unhidden objects?
        for o in sce.objects:
            if o.name != prep and not o.hide:
                o.hide = True
        
        bpy.ops.view3d.viewnumpad(type='FRONT')
        bpy.ops.view3d.view_orbit(type = 'ORBITDOWN')
        
        
        current_grease = [gp.name for gp in bpy.data.grease_pencil]        
        bpy.ops.gpencil.data_add()
        bpy.ops.gpencil.layer_add()        
        for gp in bpy.data.grease_pencil:
            if gp.name not in current_grease:           
                print(gp.name)
                gplayer = gp.layers[0]
                gp.draw_mode = 'SURFACE'
                gp.name = margin + '_tracer'
                gplayer.info = margin + '_tracer'
        
        return {'FINISHED'}
    
class WalkAroundMargin(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.walk_around_margin'
    bl_label = "Walk Around Margin"
    bl_options = {'REGISTER','UNDO'}
    
    resolution = bpy.props.IntProperty(name="Resolution", description="Number of sample points", default=50, min=0, max=100, options={'ANIMATABLE'})
    extra = bpy.props.IntProperty(name="Extra", description="Extra Stes", default=4, min=0, max=10, options={'ANIMATABLE'})    
    search = bpy.props.FloatProperty(name="Width of Search Band", description="", default=1.25, min=.2, max=2, step=5, precision=2, options={'ANIMATABLE'})
    
    def invoke(self, context, event): 
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        
        
        sce=bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        prep = tooth.prep_model
        margin = str(a + "_Margin")
        
        Prep = bpy.data.objects[prep]
        Prep.hide = False
        
        master=sce.master_model
        Master = bpy.data.objects[master]
        
        #Set up the rotation center as the 3d Cursor
        for A in bpy.context.window.screen.areas:
            if A.type == 'VIEW_3D':
                for s in A.spaces:
                    if s.type == 'VIEW_3D':
                        s.pivot_point = 'CURSOR'
                        
        #Get the prep BBox center for later       
        prep_cent = Vector((0,0,0))
        for v in Prep.bound_box:
            prep_cent = prep_cent + Prep.matrix_world * Vector(v)
        Prep_Center = prep_cent/8
        
        gp_margin = bpy.data.grease_pencil[margin + "_tracer"]
        bpy.ops.gpencil.convert(type = 'PATH')
        bpy.ops.object.convert(target = 'MESH')
        
        #get our data
        ob = bpy.context.object
        data = ob.data
        
        #place the intitial shrinkwrap modifier
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = ob.modifiers[0]
        mod.target=Prep
        mod.show_in_editmode = True
        mod.show_on_cage = True
        
        bpy.ops.object.modifier_copy(modifier = mod.name)
        
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        
        #test the resolution of the stroke
        #subdivide if necessary
        
        
        #flatten and space to make my simple curvature more succesful :-)
        bpy.ops.mesh.looptools_flatten(influence=90, plane='best_fit', restriction='none')
        bpy.ops.mesh.looptools_space(influence=90, input='selected', interpolation='cubic')
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.modifier_apply(modifier = ob.modifiers[1].name)
        
        #Now we should essentially have a nice, approximately 2D and evenly spaced line
        #And we will find the sharpest point and save it.
        verts = data.vertices
        v_ind = [v.index for v in data.vertices]
        eds = [e for e in data.edges if e.select]
        ed_vecs = [(verts[e.vertices[1]].co - verts[e.vertices[0]].co) for e in eds]
        locs = []
        curves = []

        for i in range(3,len(eds)-3):
            a1 = ed_vecs[i-1].angle(ed_vecs[i+1])
            a2 = ed_vecs[i-2].angle(ed_vecs[i+2])
            a3 = ed_vecs[i-3].angle(ed_vecs[i+3])
    
            l1 = ed_vecs[i-1].length + ed_vecs[i+1].length
            l2 = ed_vecs[i-2].length + ed_vecs[i+2].length
            l3 = ed_vecs[i-3].length + ed_vecs[i+3].length
    
    
            curve = 1/6 * (3*a1/l1 + 2 * a2/l2 + a3/l3)
            curves.append(curve)
    
        c = max(curves)
        n = curves.index(c)
        max_ed = eds[n+3] #need to check this indexing
        loc = .5 * (verts[max_ed.vertices[0]].co + verts[max_ed.vertices[1]].co)
        
        
        locs.append(loc)

        
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        bpy.context.scene.cursor_location = locs[0]
        bpy.ops.transform.resize(value = (0,0,1))
        bpy.ops.mesh.looptools_space(influence=100, input='selected', interpolation='cubic')
        
        bpy.context.scene.cursor_location = Prep_Center
        bpy.ops.transform.rotate(value = (2*pi/self.resolution,), axis = (0,0,1))
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.modifier_copy(modifier = mod.name)
        bpy.ops.object.modifier_apply(modifier = ob.modifiers[1].name)
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        bpy.ops.mesh.looptools_flatten(influence=90, plane='best_fit', restriction='none')
        bpy.ops.mesh.looptools_space(influence=90, input='selected', interpolation='cubic')
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        for b in range(1,self.resolution+self.extra):
            verts = data.vertices
            eds = [e for e in data.edges if e.select]
            ed_vecs = [(verts[e.vertices[1]].co - verts[e.vertices[0]].co) for e in eds]
            curves = []

            for i in range(3,len(eds)-3):
                a1 = ed_vecs[i-1].angle(ed_vecs[i+1])
                a2 = ed_vecs[i-2].angle(ed_vecs[i+2])
                a3 = ed_vecs[i-3].angle(ed_vecs[i+3])
    
                l1 = ed_vecs[i-1].length + ed_vecs[i+1].length
                l2 = ed_vecs[i-2].length + ed_vecs[i+2].length
                l3 = ed_vecs[i-3].length + ed_vecs[i+3].length
    
    
                curve = 1/6 * (3*a1/l1 + 2 * a2/l2 + a3/l3)
                curves.append(curve)
    
            c = max(curves)
            n = curves.index(c)
            max_ed = eds[n+3] #need to check this indexing
            loc = .5 * (verts[max_ed.vertices[0]].co + verts[max_ed.vertices[1]].co)
        
            locs.append(loc)
            
            
            
            bpy.ops.object.mode_set(mode = 'EDIT')
            
            bpy.context.scene.cursor_location = locs[b]
            zscale = self.search/ob.dimensions[2]  #if the shrinkwrapping has resulted in contraction or dilation, we want to fix that.
            bpy.ops.transform.resize(value = (0,0,zscale))
            bpy.ops.mesh.looptools_space(influence=100, input='selected', interpolation='cubic')
        
            bpy.context.scene.cursor_location = Prep_Center
            
            COM = get_com(data,v_ind,'')
            delt = locs[b] - COM
            
            bpy.ops.transform.translate(value = (delt[0], delt[1], delt[2]))
            bpy.ops.transform.rotate(value = (2*pi/self.resolution,), axis = (0,0,1))
            
            
        
            bpy.ops.object.mode_set(mode = 'OBJECT')
            bpy.ops.object.modifier_copy(modifier = mod.name)
            bpy.ops.object.modifier_apply(modifier = ob.modifiers[1].name)
            bpy.ops.object.mode_set(mode = 'EDIT')
        
            bpy.ops.mesh.looptools_flatten(influence=90, plane='best_fit', restriction='none')
            bpy.ops.mesh.looptools_space(influence=90, input='selected', interpolation='cubic')
            
            bpy.ops.object.mode_set(mode = 'OBJECT')
            bpy.ops.object.modifier_copy(modifier = mod.name)
            bpy.ops.object.modifier_apply(modifier = ob.modifiers[1].name)
            bpy.ops.object.mode_set(mode = 'EDIT')
            
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
        
        margin_data = bpy.data.meshes.new(margin)
        
        edges = []
        for i in range(0,len(locs)-1):
            edges.append([i,i+1])
        edges.append([len(locs)-1,0])
        faces = []
        
        margin_data.from_pydata(locs,edges,faces)
        margin_data.update()
        
        Margin = bpy.data.objects.new(margin, margin_data)
        sce.objects.link(Margin)
        
        current_objects = list(bpy.data.objects)
        bpy.ops.mesh.primitive_uv_sphere_add(size = .1)
        
        for ob in sce.objects:
            if ob not in current_objects:
                ob.name = margin + "_marker"
                ob.parent = Margin
                me = ob.data
                me.materials.append(bpy.data.materials['intaglio_material'])
        
        Margin.dupli_type = 'VERTS'
        Margin.parent = Master     
        tooth.margin = margin
       
        return {'FINISHED'}  
    
        
class FinalizeMargin(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.finalize_margin'
    bl_label = "Finalize Margin"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        

        sce=bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        prep = tooth.prep_model
        Prep = bpy.data.objects[prep]
        margin = tooth.margin
        Margin = bpy.data.objects[margin]
        Margin.dupli_type = 'NONE'
        master=sce.master_model
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        bpy.ops.object.select_all(action='DESELECT')
        
        bpy.context.tool_settings.use_snap = True
        bpy.context.tool_settings.snap_target= 'ACTIVE'
        bpy.context.tool_settings.snap_element = 'FACE'
        
        Margin.select = True
        sce.objects.active = Margin
        
        if Margin.type != 'MESH':    
            bpy.ops.object.convert()
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
        i = len(Margin.modifiers)
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = bpy.context.object.modifiers[i]
        mod.target=Prep
        mod.show_on_cage = True

        bpy.context.tool_settings.use_snap = True
        bpy.context.tool_settings.snap_target= 'ACTIVE'
        bpy.context.tool_settings.snap_element = 'FACE'
        bpy.context.tool_settings.proportional_edit = 'ENABLED'
        bpy.context.tool_settings.proportional_size=1
        
        bpy.ops.object.editmode_toggle()
        
        
        return {'FINISHED'}
    
class AcceptMargin(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.accept_margin'
    bl_label = "Accept Margin"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self, context):
        
        sce=bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        mesial = tooth.mesial
        distal = tooth.distal
        
        
        margin = str(a + "_Margin")
        Margin=bpy.data.objects[margin]
        master=sce.master_model
        Margin.dupli_type = 'NONE'
        if mesial:
            bpy.data.objects[mesial].hide = False
            
        if distal:
            bpy.data.objects[distal].hide = False
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        sce.objects.active=Margin
        Margin.hide=False
        Margin.select=True
        
        if 'Subsurf' in Margin.modifiers:
            bpy.ops.object.modifier_apply(modifier = 'Shrinkwrap')
            bpy.ops.object.modifier_apply(modifier = 'Subsurf')
        
        current_objects=list(bpy.data.objects)
       
        bpy.ops.object.duplicate()
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
        bpy.ops.view3d.snap_cursor_to_active()
        
        psuedo_margin= str(a + "_Psuedo Margin")
        tooth.pmargin = psuedo_margin
        for o in bpy.data.objects:
            if o not in current_objects:               
                o.name=psuedo_margin
        
        for mod in bpy.data.objects[psuedo_margin].modifiers:
            bpy.ops.object.modifier_apply(modifier = mod.name)
		

        ##This section needs to be replaced with new extrude function	
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.extrude_edges_move()
        bpy.ops.transform.resize(value=(1.05,1.05,1))
        bpy.ops.mesh.select_all(action="INVERT")
        bpy.ops.mesh.extrude_edges_move()
        bpy.ops.transform.resize(value=(.95,.95,1))
        bpy.ops.object.editmode_toggle()
        
        bpy.data.objects[psuedo_margin].hide=True
        
        
        bpy.ops.object.select_all(action='DESELECT')
        sce.objects.active=Margin
        Margin.select=True
        
        bpy.context.tool_settings.use_snap = False
        bpy.context.tool_settings.proportional_edit = 'DISABLED'
        
        #Now we want to overpack the verts so that when the edge of the
        #restoration is snapped to it, it won't displace them too much
        # I have estimated ~25 microns as a fine linear packin
        #density....another option is to leave the curve as an
        #implicit function.... hmmmmm
        
        bpy.ops.object.editmode_toggle()
        
        me=Margin.data
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        sel_edges=[e for e in me.edges if e.select == True]       
        num_edges=len(sel_edges)
        
           
        L_tot=0  #sum length of all the edges
        for e in sel_edges:
            v0=me.vertices[e.vertices[0]].co
            v1=me.vertices[e.vertices[1]].co
            V=Vector(v1-v0)
            L_tot = L_tot + pow((V.length*V.length),.5)
        
        L_avg = L_tot/num_edges  #the average edge length ~ avg vertex spacing
        
        
        res=.025  #reasonable guess for a decent vertex packing
        
        subdivs = ceil(log(L_avg/res)/log(2))  #the number of subdivisions needed to reach the target resoultion
        
        #if we are more dense than the target, then this will be negative....and that's not good
        if subdivs > 0:
            bpy.ops.mesh.subdivide(number_cuts=subdivs)
            
        #relax spacing and remove any excess vertices
        
        bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='1', regular=True) 
        bpy.ops.mesh.remove_doubles(mergedist = res*.85)
        
        bpy.ops.object.editmode_toggle()
        
        for mod in Margin.modifiers:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        

        
        return {'FINISHED'}
    
class MinThickness(bpy.types.Operator):
    ''''''
    bl_idname='view3d.min_thickness'
    bl_label="Min Thickness"
    bl_options = {'REGISTER','UNDO'}
    
    #properties
    thickness = bpy.props.FloatProperty(name="Min. Thickness", description="thickness required by material", default=0.75, min=.2, max=2, step=5, precision=2, options={'ANIMATABLE'})
    init_smoothing = bpy.props.IntProperty(name="Initial Smoothing", description="Initial Smoothing Iterations", default=15, min=0, max=30, options={'ANIMATABLE'})     
    final_smoothing = bpy.props.IntProperty(name="Final Smoothing", description="Final Smoothing Iterations", default=3, min=0, max=10, options={'ANIMATABLE'})

    def execute(self, context):
        
        sce=bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        master=sce.master_model
        Master = bpy.data.objects[master]
        
        for A in bpy.context.window.screen.areas:
            if A.type == 'VIEW_3D':
                for s in A.spaces:
                    if s.type == 'VIEW_3D':
                        s.pivot_point = 'MEDIAN_POINT'
                        
                        
        #make sure the pivot point is set correctly
        
        prep = tooth.prep_model
        Prep = bpy.data.objects[prep]
        
        margin = tooth.margin
        Margin=bpy.data.objects[margin]
        
        mat = bpy.data.materials['opposing_material']
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        sce.objects.active=Margin
        Margin.hide=False
        Margin.select=True
        
        ### Duplicate the Margin
        current_objects=list(bpy.data.objects)       
        bpy.ops.object.duplicate()        
        
        name = str(a + '_Bubble')
        for o in bpy.data.objects:
            if o not in current_objects:               
                o.name=name
                o.data.name=name
        Bubble = bpy.data.objects[name]
        
        #add in property there where tooth.bubble = name
        
        for mod in Bubble.modifiers:
            bpy.ops.object.modifier_apply(modifier = mod.name)
        bpy.ops.object.transform_apply(location = True)   
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = Bubble.modifiers[0]
        mod.target = Margin
        mod.wrap_method = 'NEAREST_VERTEX'
        
        ### Go into edit mode and remove the doubles
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.remove_doubles(mergedist = self.thickness*.85)
        bpy.ops.mesh.looptools_space(influence=90, input='selected', interpolation='cubic')
        
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        for mod in Bubble.modifiers:
            bpy.ops.object.modifier_apply(modifier = mod.name)
        
        ### Go into edit mode and extrude the first edge up a little
        ### more than the min thickness to give a "collar" around
        ### the finish line
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.extrude_edges_move()
        bpy.ops.transform.translate(value = (0,0,self.thickness*1.1))
        
        ### Back into object mode to update data
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
           
        ### Find the distance between bbtop of prep and COM of margin loop
        prep_bbox = Prep.bound_box
        prep_mx = Prep.matrix_world
        tops = []
        for v in prep_bbox:
            V = prep_mx * Vector(v)
            tops.append(V[2])
        top = max(tops)    
        print(top) 
            
        me = Bubble.data
        mx = Bubble.matrix_world
        sel_verts = [v.index for v in me.vertices if v.select]
        COM = get_com(me,sel_verts,mx)
        
        print(COM)
        
        dist = top - COM[2]
        
        steps = ceil(dist/self.thickness)
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        n=len(Bubble.vertex_groups)
        bpy.ops.object.vertex_group_add()
        Bubble.vertex_groups[n].name='Bubble'
        
        bpy.context.tool_settings.vertex_group_weight = 1
        
        
        
        for i in range(0,steps):
            bpy.ops.mesh.extrude_edges_move()
            bpy.ops.object.vertex_group_assign()
            bpy.ops.transform.translate(value = (0,0,self.thickness))
            bpy.ops.mesh.looptools_flatten(influence=45, plane='best_fit', restriction='none')
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        me = Bubble.data
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        sel_edges = [e for e in me.edges if e.select]   #notice these are Mesh Data Edges
        fill_loop_scale(Bubble, sel_edges, self.thickness)
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.vertex_group_select()  #filled_hole is still the active group
        bpy.ops.object.vertex_group_set_active(group = 'Bubble')
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_select()
        
        bpy.ops.mesh.vertices_smooth(repeat = self.init_smoothing)
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.transform_apply(rotation = True)
        
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Bubble.modifiers['Shrinkwrap']
        mod.vertex_group = 'Bubble'
        mod.offset = self.thickness
        mod.use_keep_above_surface = True
        mod.target = Prep
        
        
        bpy.ops.object.modifier_add(type = 'SMOOTH')
        mod = Bubble.modifiers['Smooth']
        mod.vertex_group = 'Bubble'
        mod.iterations = self.final_smoothing
        
        dat = Bubble.data
        dat.materials.append(mat)
        Bubble.show_transparent = True

        tooth.bubble = Bubble.name
        
        return{'FINISHED'}
    
class CementGap(bpy.types.Operator):
    ''''''
    bl_idname='view3d.cem_gap'
    bl_label="Cement Gap"
    bl_options = {'REGISTER','UNDO'}
    
    #properties
    gap = bpy.props.FloatProperty(name="Gap Thickness", description="thickness required for cement", default=0.07, min=.01, max=.5, step=2, precision=2, options={'ANIMATABLE'})
    seal = bpy.props.FloatProperty(name="Holy Zone", description="width of marginal seal", default=0.5, min=.2, max=2, step=5, precision=2, options={'ANIMATABLE'})
    chamfer = bpy.props.FloatProperty(name="Chamfer", description="0 = shoulder 1 = feather", default=.2, min=0, max=1, step=2, precision=2, options={'ANIMATABLE'})
    
    init_smoothing = bpy.props.IntProperty(name="Initial Smoothing", description="Initial Smoothing Iterations", default=15, min=0, max=30, options={'ANIMATABLE'})     
    final_smoothing = bpy.props.IntProperty(name="Final Smoothing", description="Final Smoothing Iterations", default=15, min=0, max=30, options={'ANIMATABLE'})

    def execute(self, context):
        
        sce=bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        master=sce.master_model
        Master = bpy.data.objects[master]
        
        prep = tooth.prep_model
        Prep = bpy.data.objects[prep]
        
        margin = tooth.margin
        Margin=bpy.data.objects[margin]
        
    
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        sce.objects.active=Margin
        Margin.hide=False
        Margin.select=True
        
        ### Duplicate the Margin
        current_objects=list(bpy.data.objects)       
        bpy.ops.object.duplicate()        
        
        name = str(a + '_Gap')
        for o in bpy.data.objects:
            if o not in current_objects:               
                o.name=name
                o.data.name=name
        Gap = bpy.data.objects[name]
       
        
        for mod in Gap.modifiers:
            bpy.ops.object.modifier_apply(modifier = mod.name)
        bpy.ops.object.transform_apply(location = True, rotation = True)
        
        n = len(Gap.modifiers) 
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = Gap.modifiers[n]
        mod.target = Margin
        mod.wrap_method = 'NEAREST_VERTEX'
        
        ### Go into edit mode and remove the doubles
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.remove_doubles(mergedist = self.seal*.85)
        bpy.ops.mesh.looptools_space(influence=90, input='selected', interpolation='cubic')
        
        
        
        #Object mode and apply margin modifier
        #Add shrinkwrap to prep modifier
        bpy.ops.object.mode_set(mode = 'OBJECT')
        for mod in Gap.modifiers:
            bpy.ops.object.modifier_apply(modifier = mod.name)
        
        n = len(Gap.modifiers) 
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = Gap.modifiers[n]
        mod.target = Prep
        mod.wrap_method = 'NEAREST_SURFACEPOINT'
        ### Go into edit mode and translate the margin outer edge
        ### from the margin inward the width of the marginal seal
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        me = Gap.data
        sel_edges=[e for e in me.edges if e.select == True]
        
        extrude_edges_in(me, sel_edges, Gap.matrix_world, self.seal)
        trans = Vector((0,0,self.seal*.9*self.chamfer))
        bpy.ops.transform.translate(value = trans)
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        for mod in Gap.modifiers:
            bpy.ops.object.modifier_apply(modifier = mod.name)
           
        ### Find the distance between bbtop of prep and COM of margin loop
        prep_bbox = Prep.bound_box
        prep_mx = Prep.matrix_world
        tops = []
        for v in prep_bbox:
            V = prep_mx * Vector(v)
            tops.append(V[2])
        top = max(tops)    
        print(top) 
            
        me = Gap.data
        mx = Gap.matrix_world
        sel_verts = [v.index for v in me.vertices if v.select]
        COM = get_com(me,sel_verts,mx)
        
        dist = top - COM[2]
        
        steps = ceil(dist/self.seal)
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        n=len(Gap.vertex_groups)
        bpy.ops.object.vertex_group_add()
        Gap.vertex_groups[n].name='Gap'
        
        bpy.context.tool_settings.vertex_group_weight = .2
        bpy.ops.object.vertex_group_assign()
        bpy.context.tool_settings.vertex_group_weight = 1
        
        for i in range(0,steps):
            bpy.ops.mesh.extrude_edges_move()
            bpy.ops.object.vertex_group_assign()
            bpy.ops.transform.translate(value = (0,0,self.seal))
            bpy.ops.mesh.looptools_flatten(influence=45, plane='best_fit', restriction='none')
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        me = Gap.data
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        sel_edges = [e for e in me.edges if e.select]   #notice these are Mesh Data Edges
        fill_loop_scale(Gap, sel_edges, self.seal)
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.vertex_group_select()  #filled_hole is still the active group
        bpy.ops.object.vertex_group_set_active(group = 'Gap')
        bpy.ops.object.vertex_group_assign()
        bpy.ops.object.vertex_group_select()
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.mesh.select_non_manifold()
        
        n = len(Gap.vertex_groups)
        bpy.ops.object.vertex_group_assign(new = True)
        Gap.vertex_groups[n].name = 'Edge'
        
        bpy.ops.mesh.select_all(action = 'SELECT')
        #very important step for ensuring projections onto this surface work later!
        bpy.ops.mesh.normals_make_consistent()
           
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        n = len(Gap.modifiers)
        bpy.ops.object.modifier_add(type = 'SMOOTH')
        mod = Gap.modifiers[n]
        mod.name = 'Init Smooth'        
        mod.vertex_group = 'Gap'
        mod.factor = .75
        mod.iterations = self.init_smoothing
        
        n = len(Gap.modifiers)
        bpy.ops.object.modifier_add(type = 'MULTIRES')
        mod = Gap.modifiers[n]
        bpy.ops.object.multires_subdivide(modifier="Multires")
        bpy.ops.object.multires_subdivide(modifier="Multires")
        mod.levels=1
        
        n = len(Gap.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Gap.modifiers[n]
        mod.name = '1st Shrinkwrap'
        mod.vertex_group = 'Gap'
        mod.use_keep_above_surface = True
        mod.target = Prep
        
        n = len(Gap.modifiers)
        bpy.ops.object.modifier_add(type = 'SMOOTH')
        mod = Gap.modifiers[n]
        mod.name = 'Final Smooth'        
        mod.vertex_group = 'Gap'
        mod.iterations = self.final_smoothing
        
        n = len(Gap.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Gap.modifiers[n]
        mod.name = '2nd Shrinkwrap'
        mod.vertex_group = 'Gap'
        mod.use_keep_above_surface = True
        mod.target = Prep
        mod.offset = self.gap
        
        
        n = len(Gap.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Gap.modifiers[n]
        mod.name = 'Blend'
        mod.wrap_method = 'PROJECT'
        mod.use_project_x = False
        mod.use_project_y = False
        mod.use_project_z = True
        mod.vertex_group = 'Edge'
        mod.use_keep_above_surface = True
        mod.use_positive_direction = False
        mod.use_negative_direction = True
        mod.cull_face = 'BACK'
        mod.target = Prep
        
        
        
        
        mat=bpy.data.materials["intaglio_material"]
        Gap.data.materials.append(mat)
        
        
        return{'FINISHED'}    
 
class PrepFromMargin(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.prep_from_margin'
    bl_label = "Prep From Margin"
    bl_options = {'REGISTER','UNDO'}
    
    hz_width = bpy.props.FloatProperty(name="Holy Zone", description="Width of marginal seal", default=0.5, min=.2, max=2, step=5, precision=2, options={'ANIMATABLE'})
    cem_gap = bpy.props.FloatProperty(name="Cement Gap", description="Thickness of CG", default=0.05, min=.02, max=.2, step=2, precision=2, options={'ANIMATABLE'})
    margin_quality = bpy.props.FloatProperty(name="Margin Quality", description="0 for shoulder 1 for knife", default=0.25, min=0, max=1, step=5, precision=2, options={'ANIMATABLE'})
    
    res = bpy.props.FloatProperty(name="resolution", description="vertex spacing", default=0.1, min=.02, max=.2, step=1, precision=3, options={'ANIMATABLE'})        
    feather = bpy.props.IntProperty(name="Blend Zone", description="Transition from HZ to CG", default=3, min=1, max=10, options={'ANIMATABLE'})
    final_smoothing = bpy.props.IntProperty(name="Final Smoothing", description="Final Smoothing Iterations", default=3, min=0, max=10, options={'ANIMATABLE'})
    
    def execute(self, context):
        
        sce=bpy.context.scene
        j = bpy.context.scene.working_tooth_index
        a = bpy.context.scene.working_teeth[j].name
        master=sce.master_model
        Master = bpy.data.objects[master]
        margin = str(a + "_Margin")
        Margin=bpy.data.objects[margin]
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        sce.objects.active=Margin
        Margin.hide=False
        Margin.select=True
        
        ### Duplicate the Margin
        current_objects=list(bpy.data.objects)       
        bpy.ops.object.duplicate()        
                
        prep= str(a + "_Prep")
        
        for o in bpy.data.objects:
            if o not in current_objects:               
                o.name=prep
                o.data.name=prep
        Prep = bpy.data.objects[prep]
        for mod in bpy.data.objects[prep].modifiers:
            bpy.ops.object.modifier_apply(modifier = mod.name)
        
        
        
        
        ### Place the Object Origin at 0,0,0 and apply rotation
        bpy.ops.view3d.snap_cursor_to_center()                
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        bpy.ops.object.transform_apply(rotation = True)
        
        ### Extrude and Translate down
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.extrude_edges_move()
        bpy.ops.transform.translate(value = Vector((0,0,-10)))
        
        ### Set View to Above
        bpy.ops.view3d.viewnumpad(type = 'TOP', align_active = False)
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        ### Flatten
        bpy.ops.mesh.looptools_flatten(influence=100, plane='best_fit', restriction='none')
        
        ### Fill
        bpy.ops.mesh.fill()
        ###  Create a vertex Group for Cement Gap
                
        n=len(bpy.data.objects[prep].vertex_groups)
        bpy.ops.object.vertex_group_add()
        bpy.data.objects[prep].vertex_groups[n].name="Cement Gap"
        
        
        ###  Create a vertex Group for Holy Zone
        n=len(bpy.data.objects[prep].vertex_groups)
        bpy.ops.object.vertex_group_add()
        bpy.data.objects[prep].vertex_groups[n].name="Holy Zone"
        bpy.ops.object.vertex_group_set_active(group='Holy Zone')
        
        ###  Calculate number of extrusions for HZ
        iters = ceil(self.hz_width/self.res)
        
        
        ###  Add shrinkwrap to master Modifier
        n=len(Prep.modifiers)
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = Prep.modifiers[n]
        mod.wrap_method='NEAREST_SURFACEPOINT'        
        mod.offset=0
        mod.vertex_group='Holy Zone'
        mod.target=bpy.data.objects[master]
        mod.name='Holy Zone'
        mod.show_expanded=False
        
        
        ###  Extrude Edges In for number of extrusion
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.mesh.select_non_manifold()
        me = Prep.data
        mx = Prep.matrix_world
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        
        for i in range(0,iters):
            
            bpy.ops.mesh.select_non_manifold()
            bpy.ops.mesh.remove_doubles(mergedist = self.res*.75)
            bpy.ops.mesh.extrude_edges_move()
            bpy.ops.object.mode_set(mode = 'OBJECT')
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.object.vertex_group_assign()
            
            #extrude_edges_in
            sel_edges=[e for e in me.edges if e.select]
            extrude_edges_in(me, sel_edges, mx, self.res)
            #translate up proportional to margin quality
            bpy.ops.mesh.select_non_manifold()
            bpy.ops.transform.translate(value=Vector((0,0,self.margin_quality*self.res)))
            #assign to vertex group HZ
            #copy modifier
            #apply modifier
            
            
            

        ### Apply HZ shrinkwrap modifier
        
        ### Make Cement Gap active VG
           
        ### Calculate number of extruzions for feather
            #extrude
            #extrude_edges_in
            #loop relax
            #remove doubles
            #translate up by a larger factor
            #Set  vertex group weight
            #Assign to vertex group Cement Gap
            
      
        
        ### Hole filler, translate up, flatten, scale slightly, smooth, project down
        ### Add shrinkwrap modifier with cement gap offset and keep above surface
        
        
        ### Add shrinkwrap modifier with cement gap offset and keep above surface
        ### Smooth filled hole a few iterations.
        
            
        print(self.res)
        print(self.hz_width)
        
        return{'FINISHED'}
    
    
class GetCrownForm(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.get_crown_form'
    bl_label = "Get Crown Form"
    bl_options = {'REGISTER','UNDO'}
    
    objects = [] 
    for index, object in enumerate(bpy.data.scenes['Data'].objects):
        objects.append((str(index), object.name, str(index))) 

    ob_list = bpy.props.EnumProperty(name="Tooth Library Objects", description="A List of the tooth library", items=objects, default='0')
        
    
    def invoke(self, context, event): 
        
        #context.window_manager.invoke_search_popup(self.ob_list)
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        
        
        sce=bpy.context.scene
        master=sce.master_model
        Master=sce.objects[master]
        
        #Here is where I need to distinguish between the active prep and the
        #Crown template model to use.
        
        j = bpy.context.scene.working_tooth_index
        tooth = bpy.context.scene.working_teeth[j]
        a = tooth.name
        new_name=str(a + "_FullContour")
        
        if tooth.rest_type == '0' or tooth.rest_type == '1':
            tooth.restoration = new_name
            
        tooth.contour = new_name
        
        crown_to_use = int(self.properties.ob_list)
               
        ob = bpy.data.scenes['Data'].objects[crown_to_use].copy() 
        new_data = ob.data.copy()
        new_data.name = new_name
        ob.name = new_name
        ob.data = new_data
        
        ob.data.user_clear()
        sce.objects.link(ob)
        
        ob.data.use_fake_user = True #can't remember why I did this
        sce.objects.active=ob
        
        ob.parent=Master
        bpy.ops.object.select_all(action='DESELECT')
        ob.select=True
        bpy.ops.object.rotation_clear()
        bpy.ops.view3d.snap_selected_to_cursor()
        Master.hide=False
        

        
        bpy.ops.object.shade_smooth()
        
        mat1=bpy.data.materials["restoration_material"]
        ob.data.materials.append(mat1)
        
        if tooth.rest_types[int(tooth.rest_type)] == 'PONTIC':
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.mesh.select_non_manifold()
            bpy.ops.mesh.looptools_flatten(influence = 100, plane = 'best_fit', restriction = 'none')
            bpy.ops.transform.translate(value = (0,0,-1))
            bpy.ops.object.hole_filler()
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_more()
            bpy.ops.mesh.select_more()
            bpy.ops.mesh.remove_doubles()
            bpy.ops.mesh.relax(iterations=10)
            bpy.ops.mesh.vertices_smooth(repeat = 5)
            bpy.ops.object.mode_set(mode='OBJECT')
            
            bpy.ops.object.multires_base_apply(modifier = 'Multires')
            bpy.ops.object.modifier_remove(modifier = 'Multires')
            bpy.ops.object.modifier_add(type = 'MULTIRES')
            for i in range(0,3):
                bpy.ops.object.multires_subdivide(modifier = 'Multires')
            
            
        
        
        return {'FINISHED'}
    
    def draw(self, context):
        
        layout = self.layout
        box = layout.box()
        box.label("Choose A Template")
        box.prop(self, "ob_list")





#This function takes the bounding boxes of the mesial and distal models and uses them
#to guestimate the scale, rotataion and location of the crown template.
#it's accuracy depends on the height of contour in the mesial and distal models defining
#the edge of the bounding box.  Tissue extedning beyond the HOC will cause bad results.
#At this poing I have not added in rotation bucco/lingually or mesio distally.  Soon
class AutoRough(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.auto_rough'
    bl_label = "Auto Rough"
    
    
    def execute(self, context):
        
        sce=bpy.context.scene
        master=sce.master_model
        Master=sce.objects[master]
        
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        restoration=tooth.restoration
        Restoration=sce.objects[restoration]
        
        if tooth.bubble:
            bubble = tooth.bubble
            Bubble = sce.objects[bubble]
            print('there is a bubble')
            print('using bubble to place and scale restoration')
            
            rest_cent = Vector((0,0,0))
            for v in Restoration.bound_box:
                rest_cent = rest_cent + Restoration.matrix_world*Vector(v)
            Rest_Center = rest_cent/8
            
            bub_cent = Vector((0,0,0))
            for v in Bubble.bound_box:
                bub_cent = bub_cent + Bubble.matrix_world * Vector(v)
            Bub_Center = bub_cent/8
            
            print(Rest_Center)
            print(Bub_Center)
            
            trans = Bub_Center - Rest_Center
            
            bpy.ops.object.select_all(action = 'DESELECT')
            sce.objects.active = Restoration
            Restoration.select = True
            
            bpy.ops.transform.translate(value = trans)
            rest_dim = Restoration.dimensions
            bub_dim = Bubble.dimensions
        
            x_scale = bub_dim[0]/rest_dim[0]
            y_scale = bub_dim[1]/rest_dim[1]
            z_scale = bub_dim[2]/rest_dim[2]
          
            #Scale the template to match the min thickness bubble        
        
            bpy.ops.transform.resize(value =  (x_scale*1.25, y_scale*1.05, z_scale*1.4))
            bpy.ops.transform.translate(value = Vector((0,0,1.25)))
            
        if tooth.mesial and tooth.distal:
            mesial=tooth.mesial
            Mesial=sce.objects[mesial]
            print('there is a mesial')
            
            distal=tooth.distal            
            Distal=sce.objects[distal]
            print('there is a distal')
        
            mes_cent = Vector((0,0,0))
            for v in Mesial.bound_box:
                mes_cent = mes_cent + Mesial.matrix_world * Vector(v)
            Mes_Center = mes_cent/8
            
            
            dis_cent = Vector((0,0,0))
            for v in Distal.bound_box:
                dis_cent = dis_cent + Distal.matrix_world * Vector(v)
            Dis_Center = dis_cent/8
            
            #find the midpoint of the distal face of the mesial bounding box
            
            distal_point = Dis_Center + Vector((Distal.dimensions[0]/2,0,0))
            mesial_point = Mes_Center - Vector((Mesial.dimensions[0]/2,0,0))
            
            
            ###test by adding a sphere at the mesial and distal points
            
            sce.cursor_location = distal_point
            print(distal_point)
            
            print(mesial_point)
            sce.cursor_location = mesial_point
            
            '''            
            MX=Master.matrix_world
            L_mes=Mesial.location
            L_dis=Distal.location
            L_res=Restoration.location*MX
            BB_mes=Mesial.bound_box
            BB_dis=Distal.bound_box
            point_m=Vector(BB_mes[0])
            point_d=Vector(BB_dis[7])
        
            target_mes=L_mes*MX+Vector((point_m[0],0,0))
            target_dis=L_dis*MX+Vector((point_d[0],0,0))
            
            ip_vec=target_mes-target_dis
        
            d_m_vec=Vector((ip_vec[0], ip_vec[1],0))
        
        
            scale=d_m_vec.length/Restoration.dimensions[0]
            print(str(scale))
        
            z_rotation=d_m_vec.angle(Vector((1,0,0)))
            print("the z rotation is " + str(z_rotation))    
        
            #this is in the parent reference frame so no MX_world
            dm_location=Distal.location*.5+Mesial.location*.5
        
            new_location=Vector((dm_location[0],dm_location[1],Restoration.location[2]))
            print("the new location is " + str(new_location))
        
            Restoration.location=new_location
            Restoration.rotation_euler=Vector((0,0,z_rotation))
            Restoration.scale=Vector((1.08*scale,scale,scale,))
            '''
        
        
        return {'FINISHED'}



class GoToSculpt(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.go_to_sculpt'
    bl_label = "Go To Sculpt"
    bl_options = {'REGISTER','UNDO'}
    
    
    def execute(self, context):
        sce = bpy.context.scene
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        
        
        
        ob = bpy.context.object
        restoration=tooth.restoration
        coping = tooth.coping
        anat_cop = tooth.acoping
        contour = tooth.contour
        
        #check to see if the selected/active object in the scene
        #is one of the objects of interest.     
        if ob.name in [restoration, contour, coping, anat_cop]:
            ob.hide = False
            Restoration = ob
            
        #if some other object is selected, we will select the 
        #restoration for the user    
        else:
            if not restoration:
                self.report('WARNING',"The selected object is not of restorative significance or there is no restoration.")
                return{'CANCELLED'}
            Restoration=sce.objects[restoration]       
        
        if Restoration.data.users > 1:
            Restoration.data.use_fake_user = False
            
        bpy.ops.object.select_all(action = 'DESELECT')
        sce.objects.active = Restoration
        Restoration.select = True
        Restoration.hide = False
        
        if tooth.rest_type == '2' or tooth.rest_type == '3':
            bpy.ops.object.multires_base_apply(modifier = "Multires")
            for mod in Restoration.modifiers:
                if mod.name != 'Multires':
                    bpy.ops.object.modifier_apply(modifier = mod.name)
                    
        if tooth.rest_type == '0':
            bpy.ops.object.multires_base_apply(modifier = "Multires")
        
        mod = Restoration.modifiers['Multires']
        mod.sculpt_levels = 1
            
        bpy.ops.object.mode_set(mode='SCULPT',toggle=True)
        bpy.context.tool_settings.sculpt.use_symmetry_x = False
        bpy.context.tool_settings.sculpt.use_symmetry_y = False
        bpy.context.tool_settings.sculpt.use_symmetry_z = False
        
        Restoration.data.use_fake_user = True
        
        return {'FINISHED'}


#Trims off the smaller piece of a mesh after a cut is made.  The new vertices created
#by the cut need to be selected (which is default after using knife tool)
class TrimCut(bpy.types.Operator):
    ''''''
    bl_idname = "view3d.trim_cut"
    bl_label = "Trim Cut"
    
    
    def execute(self, context):
        obj=bpy.context.object
        n=len(obj.vertex_groups)
        bpy.ops.object.vertex_group_add()
        obj.vertex_groups[n].name="cut"
        bpy.ops.object.vertex_group_set_active(group='cut')
        bpy.ops.object.vertex_group_assign()
        bpy.ops.mesh.loop_to_region()
        bpy.ops.object.vertex_group_deselect()
        bpy.ops.mesh.delete()
        bpy.ops.object.vertex_group_remove()
        
        return {'FINISHED'}

################################################################################
#################### 80 Character PEP 8 Style Guide  ###########################
class SnapVerts2Mesh(bpy.types.Operator):
    ''''''
    bl_idname = 'object.snap_verts_mesh'
    bl_label = "Snap Verts 2 Mesh"
    bl_options = {'REGISTER','UNDO'}
    
    rest_types=['CONTOUR',
                'PONTIC',
                'COPING',
                'ANATOMIC COPING']

    rest_name = bpy.props.StringProperty(name="Tooth Number",default="")
    influence = bpy.props.FloatProperty(name="Nearby Influence", description="", default=1, min=.1, max=2, step=2, precision=1, options={'ANIMATABLE'}) 
    
    def execute(self, context):
        
        #Force the correct mode and identify the working tooth, restoration &
        #margin
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        
        bpy.context.tool_settings.vertex_group_weight = 1
                
        sce = bpy.context.scene        
        j = bpy.context.scene.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        
        if self.rest_name:
            restoration = self.rest_name
        
        else:
            restoration = tooth.contour  #may need to clean this up later
        
        Restoration=bpy.data.objects[restoration]
        
        margin = tooth.margin
        Margin=bpy.data.objects[margin]

        Restoration.select = True
        sce.objects.active = Restoration
        
        #tranform operators use world coordinates so we will need
        #access to the world matrices        
        matrix1=Restoration.matrix_world
        matrix2=Margin.matrix_world 

        bpy.ops.object.mode_set(mode='EDIT')

        # Ensure non manifold edge is the margin of the crown and that it is
        #grouped correctly in case the mesh has been altered from its original
        #topology.
        if margin in bpy.context.object.vertex_groups:
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.object.vertex_group_set_active(group = margin)
            bpy.ops.object.vertex_group_remove_from()
            
            
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold()
        
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        
        if margin not in Restoration.vertex_groups:
            n=len(Restoration.vertex_groups)
            bpy.ops.object.vertex_group_assign(new=True)
            Restoration.vertex_groups[n].name = margin
        else:
            bpy.ops.object.vertex_group_set_active(group = margin)
            bpy.ops.object.vertex_group_assign()
            
        ####  Condense fill loops up to equator start ###
        #################################################
        
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        #only for testing
        #time.sleep(.5)
        #bpy.ops.wm.redraw()
        
        #count the number of vertices in the margin loop and therefore in
        #the equator loop and any fill loops in  between.
        Restoration=bpy.data.objects[restoration]
        vs = Restoration.data.vertices
        sverts = [v for v in vs if v.select]
        vperl = len(sverts)  #verts per loop
        print('there are' + str(vperl) + ' verts in the loop')
        
        bpy.ops.object.vertex_group_set_active(group = 'Equator')
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.loop_to_region()      
        
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        
        #only for testing
        #time.sleep(.5)
        #bpy.ops.wm.redraw()
        Restoration=bpy.data.objects[restoration]
        vs = Restoration.data.vertices
        sverts = [v for v in vs if v.select]
        print(str(len(sverts)))
        
        n_loops = len(sverts)/vperl - 2
        print('nloops is' + str(n_loops))
        
        
        if n_loops == 2:
            bpy.ops.object.vertex_group_set_active(group = margin)
            bpy.ops.object.vertex_group_deselect()    
            bpy.ops.mesh.select_less()
            
            
            ## ###Toggle for selection and groups to udpate #####
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.editmode_toggle()

            
            #establish COM of loop to test which way to edge slide
            Restoration=bpy.data.objects[restoration]
            vs = Restoration.data.vertices
            sverts = [v for v in vs if v.select]
            svl = Vector((0,0,0))
            for v in sverts:
                svl= svl + v.co
            n = len(sverts)
            svl_i = matrix1 * (svl/n)
            
            bpy.ops.transform.edge_slide(value = .01)
            
            ## ###Toggle for selection and groups to udpate #####
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.editmode_toggle()
            
            #establish new COM of loop to test which way to edge slide
            Restoration=bpy.data.objects[restoration]
            vs = Restoration.data.vertices
            sverts = [v for v in vs if v.select]
            svl = Vector((0,0,0))
            for v in sverts:
                svl= svl + v.co
            n = len(sverts)
            svl_f = matrix1 * (svl/n)
            
            if svl_f[2] > svl_i[2]:
                bpy.ops.transform.edge_slide(value = .85)
            else:
                bpy.ops.transform.edge_slide(value = -.85)
                
            #only for testing
            #bpy.ops.wm.redraw()
            #time.sleep(.5)
            
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.vertex_group_set_active(group = margin)
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.select_more()
        bpy.ops.object.vertex_group_deselect()
        Restoration=bpy.data.objects[restoration]
        vs = Restoration.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_i = matrix1 * (svl/n)
        
        bpy.ops.transform.edge_slide(value = .01)
        
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        
        #only for testing        
        #bpy.ops.wm.redraw()
        #time.sleep(.5)
            
        #establish new COM of loop to test which way to edge slide
        Restoration=bpy.data.objects[restoration]
        vs = Restoration.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_f = matrix1 * (svl/n)
        
        if svl_f[2] > svl_i[2]:
            bpy.ops.transform.edge_slide(value = .85)
        else:
            bpy.ops.transform.edge_slide(value = -.85)
        
        #only for testing        
        #bpy.ops.wm.redraw()
        #time.sleep(.5)
        
        ####  Condense fill loops up to equator ###
        ###############    End   ##################
        
        
        
        #Median of template margin match bbox cent marked margin #
        ######################  Start  ###########################
        
        #Get the bounding box center of the marked margin in world coordinates
        #(Does this require applying location/rotation to margin?        
        mbbc = Vector((0,0,0))
        for v in Margin.bound_box:
            mbbc = mbbc + matrix2 * Vector(v)
        Mbbc = mbbc/8
        
        ## Get the median point of the crown form margin
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold()  
        
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        
        Restoration=bpy.data.objects[restoration]
        vs = Restoration.data.vertices
        
        #sverts: selected vertices
        sverts = [v for v in vs if v.select]
        
        #svl: selected vertices location
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl = matrix1 * (svl/n)
        
        #The tranform.translate operator takes a vector in world coords
        trans = Mbbc - svl
        trans = Vector((0,0,trans[2]))
        bpy.ops.transform.translate(value = trans)
        
        
        bpy.ops.transform.resize(value = (1.1, 1.1, 1.1))
        
        
        #Median of template margin match bbox cent marked margin #
        ######################  End  ###########################
                 
        
        
        # Snap Crown form margin to closest marked margin point  #
        ######################  Start  ###########################
        
        
        
        #We don't know the indices of the vertices in the vertex group
        #This is my brute force way of keeping track of them for later
        #use
        
        vertex_list=[]
        vg = Restoration.vertex_groups[margin]
        vs = Restoration.data.vertices

        for v in vs:    
            for g in v.groups:
                if g.group == vg.index:
                    vertex_list.append(v.index)
        
        print(vertex_list)
        
        bpy.context.tool_settings.mesh_select_mode = [True,False,False]
        for b in vertex_list:
            
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.editmode_toggle()
            Restoration.data.vertices[b].select = True  #Select one vertex
            bpy.ops.object.editmode_toggle() 
    
            distancesmag=[]  #prepare a list of the distances to all the vertices in the other mesh
            distancesvec=[]  #Since i have to calculate this to calculate the distance i just save it in a list...poor memory management
            
            for v in Margin.data.vertices:
                distance = matrix2 * v.co - matrix1 * Restoration.data.vertices[b].co #calculate real world vector between objects
        
                distancesvec.append(distance)  #add that vector to a list
        
                #magnitude=sqrt(distance*distance)   #calculate the magnitude of that vector (eg, the distance)
                magnitude=distance.length
                
                distancesmag.append(magnitude)   #add that value to a list           
    
            smallest_distance=min(distancesmag)  #find the smallest distance (eg, the closest point)
            
            smallest_index=distancesmag.index(smallest_distance)
            
            translate=distancesvec[smallest_index]
 
 
            d_index=0
            for d in distancesmag:     #I need a good way to find the index of the smallest value. for now brute force
                if d == smallest_distance:
                    translate=distancesvec[d_index]            
                d_index+=1
  
  
            bpy.ops.transform.translate(value=translate, constraint_axis=(False, False, False), mirror=False, proportional='ENABLED', proportional_edit_falloff='SMOOTH', proportional_size=self.influence+.01, snap=False, snap_target='ACTIVE', snap_align=False, release_confirm=True)            
            bpy.ops.mesh.hide()
            
  
        bpy.ops.mesh.reveal()
        
        # Snap Crown form margin to closest marked margin point #
        ######################  End   ###########################
        
        
        # Smooth between equator and margin        #
        ##############  Start   ####################
        
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.vertex_group_set_active(group = margin)
        bpy.ops.object.vertex_group_select()
        bpy.ops.mesh.select_more()
        bpy.ops.object.vertex_group_deselect()
        
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        
        Restoration=bpy.data.objects[restoration]
        vs = Restoration.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_i =matrix1 * (svl/n) 
        
        bpy.ops.transform.edge_slide(value = .01)
        
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
            
        #establish new COM of loop to test which way to edge slide
        Restoration=bpy.data.objects[restoration]
        vs = Restoration.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_f = matrix1 * (svl/n)
        
        if svl_f[2] < svl_i[2]:
            down = 1
        else:
            down = -1
            
            
        if n_loops == 2:
            bpy.ops.transform.edge_slide(value = down*.68)
            
        else:
            bpy.ops.transform.edge_slide(value = down*.52)
            
          
        if n_loops == 2:
            bpy.ops.mesh.select_all(action = 'DESELECT')
            
            bpy.ops.object.vertex_group_set_active(group = 'Equator')
            bpy.ops.object.vertex_group_select() 
            
            
            bpy.ops.object.vertex_group_set_active(group = margin)
            bpy.ops.object.vertex_group_select()
            
            bpy.ops.mesh.loop_to_region()
            bpy.ops.object.vertex_group_deselect()
                
            bpy.ops.mesh.select_less()
            
            
            ## ###Toggle for selection and groups to udpate #####
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.editmode_toggle()
            
            #establish COM of loop to test which way to edge slide
            Restoration=bpy.data.objects[restoration]
            vs = Restoration.data.vertices
            sverts = [v for v in vs if v.select]
            svl = Vector((0,0,0))
            for v in sverts:
                svl= svl + v.co
            n = len(sverts)
            svl_i = matrix1 * (svl/n)
            
            bpy.ops.transform.edge_slide(value = .01)
            
            ## ###Toggle for selection and groups to udpate #####
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.editmode_toggle()
            
            #establish new COM of loop to test which way to edge slide
            Restoration=bpy.data.objects[restoration]
            vs = Restoration.data.vertices
            sverts = [v for v in vs if v.select]
            svl = Vector((0,0,0))
            for v in sverts:
                svl= svl + v.co
            n = len(sverts)
            svl_f = matrix1 * (svl/n)
            
            if svl_f[2] < svl_i[2]:
                down = 1
                
            else:
                down = -1
                
            bpy.ops.transform.edge_slide(value = down*.45)    
             
        
        
        
        # Smooth between equator and margin        #
        ##############   End    ####################
        
        #Add Dynamic Margin Modifier Above Multires#
        ##############   Start  ####################
        
        n=len(bpy.context.object.modifiers)
        
        margin = str(a + "_Margin")
        
        if margin not in Restoration.modifiers:
                
            bpy.ops.object.modifier_add(type='SHRINKWRAP')
            mod = Restoration.modifiers[n]
            mod.wrap_method='NEAREST_VERTEX'        
            mod.offset=0
            mod.vertex_group=margin #the vertex group in the crown form and the name of the actual margin object are the same.
            mod.target=bpy.data.objects[margin]
            mod.name = margin
            mod.show_expanded=False
        
            for i in range(0,n):
                bpy.ops.object.modifier_move_up(modifier=margin)
        
        bpy.ops.object.editmode_toggle()  
  
        return {'FINISHED'}



    
class CervicalConvergence(bpy.types.Operator):
    '''Tooltip'''
    bl_idname = "object.cervical_convergence"
    bl_label = "Angle Cervical Convergence"
    bl_options = {'REGISTER','UNDO'}

    ang = bpy.props.FloatProperty(name="ang", description="", default=15, min=0, options={'ANIMATABLE'}, subtype='NONE', unit='NONE')
    
    def execute(self, context):
        acc = self.ang
        
        sce = bpy.context.scene        
        j = bpy.context.scene.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        restoration=tooth.restoration
        Restoration=bpy.data.objects[restoration]
        matrix1 = Restoration.matrix_world
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.mesh.select_non_manifold()

        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        
        Restoration=bpy.data.objects[restoration]
        vs = Restoration.data.vertices
        margin_verts = [v.index for v in vs if v.select]
        #print(margin_verts)
        ###  Additionally Select the Next Loop (but not connecting edges)

        bpy.ops.mesh.select_more()
        bpy.ops.mesh.region_to_loop()
        ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        Restoration=bpy.data.objects[restoration]
        es = Restoration.data.edges
        exclude_edges = {e.key for e in es if e.select}
        #print(exclude_edges)
        
        bpy.ops.mesh.loop_to_region()
        ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()

        ###  With both loops selected,  Establish the edge keys of vertical edges
        Restoration=bpy.data.objects[restoration]
        es = Restoration.data.edges
        v_edges = {e.key for e in es if e.select}
        
        vert_edges = v_edges - exclude_edges
        #print(vert_edges)
        
  
        
        
        ### iterate thourhg and translate the top vertex of each vertical edge
        ### to make the proper angle of cervical convergence.
        bpy.context.tool_settings.mesh_select_mode = [True, False, False]
        bpy.ops.mesh.select_all(action='DESELECT')
        
        for key in list(vert_edges):
            bpy.ops.mesh.select_all(action='DESELECT')
            bottom = set(key) & set(margin_verts)
            
            top = set(key) - bottom
            
            b = list(bottom)
            t = list(top)
            
            bot = b[0]
            tp = t[0]
            
            #print(bot)
            #print(tp)
            
            Restoration.data.vertices[tp].select = True
            bpy.ops.object.editmode_toggle()
            Restoration.data.vertices[tp].select = True
            bpy.ops.object.editmode_toggle()
            
            v1 = matrix1 * Restoration.data.vertices[bot].co
            v2 = matrix1 * Restoration.data.vertices[tp].co
            #print(v2)
            edge_v = v2 - v1
            edge_l = edge_v.length
            n = Restoration.data.vertices[tp].normal
            N = Vector((n[0],n[1],0))
            N.normalize()
            Adjust = N*edge_l*sin(acc*pi/180)
            trans = Vector((v1[0],v1[1],v2[2])) + Adjust - v2
            
            bpy.ops.transform.translate(value = trans, release_confirm=True)
            
            #print('translating' + str(trans))
            
        bpy.ops.object.mode_set(mode = 'OBJECT')
            
        return {'FINISHED'}
        
    def draw(self, context):
        
        layout = self.layout
        row = layout.row()       
        row.prop(self, "ang")
        

class SimpleCoping(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.make_simple_coping'
    bl_label = "Simple Coping"
    bl_options = {'REGISTER','UNDO'}
    
    
    thickness = bpy.props.FloatProperty(name="Min. Thickness", description="thickness required by material", default=0.45, min=.2, max=2, step=5, precision=2, options={'ANIMATABLE'})
    ang = bpy.props.FloatProperty(name="ang", description="", default=25, min=0, max =65, options={'ANIMATABLE'}, subtype='NONE', unit='NONE')
    
    def execute(self, context):
        
        sce=bpy.context.scene
        master=sce.master_model
        Master=sce.objects[master]
        
        j = bpy.context.scene.working_tooth_index
        tooth = bpy.context.scene.working_teeth[j]
        a = tooth.name
        bubble = tooth.bubble
        margin = tooth.margin
        prep = tooth.prep_model
        
        Margin = sce.objects[margin]
        Bubble = sce.objects[bubble]
        Prep = sce.objects[prep]
        
        for A in bpy.context.window.screen.areas:
            if A.type == 'VIEW_3D':
                for s in A.spaces:
                    if s.type == 'VIEW_3D':
                        s.pivot_point = 'MEDIAN_POINT'
        
        
        new_name=str(a + "_Coping")
        coping = new_name  #fix this later
        
        if tooth.rest_type == '2':
            tooth.restoration = new_name
        
        #i leave this here in case the user is just exploring the idea of a simple coping...    
        tooth.coping = new_name
    
        #definitely need to smooth this out since it goes by name :-/
        Coping = bpy.data.scenes['Data'].objects[a].copy()
        new_data = Coping.data.copy()
        new_data.name = new_name
        Coping.name = new_name
        Coping.data = new_data
        sce.objects.link(Coping)
        Coping.data.user_clear()
        sce.objects.active=Coping
        Coping.parent=Master
        bpy.ops.object.select_all(action='DESELECT')
        Coping.select=True
        bpy.ops.object.rotation_clear()
        bpy.ops.object.shade_smooth()
         
        mat1=bpy.data.materials["restoration_material"]
        Coping.data.materials.append(mat1)
        
        
        ##Get the bounding boxes of the tooth and the bubble
        cop_cent = Vector((0,0,0))
        for v in Coping.bound_box:
            cop_cent = cop_cent + Coping.matrix_world *Vector(v)
        Cop_Center = (cop_cent/8)
        
        
        ##Get the bounding boxes of the tooth and the bubble
        bub_cent = Vector((0,0,0))
        for v in Bubble.bound_box:
            bub_cent = bub_cent + Bubble.matrix_world * Vector(v)
        Bub_Center =  (bub_cent/8)
        
        #put the restoration in the same spot as the bubble
        trans = Bub_Center - Cop_Center
        bpy.ops.transform.translate(value = trans)
        
        cop_dim = Coping.dimensions
        bub_dim = Bubble.dimensions
        
        #2.59 major error!!  Y and Z are transposed in ob.dimensions.
        x_scale = bub_dim[0]/cop_dim[0]
        y_scale = bub_dim[1]/cop_dim[1]
        z_scale = bub_dim[2]/cop_dim[2]
          
        #Scale the template to match the min thickness bubble
        
        
        bpy.ops.transform.resize(value =  (x_scale*1.2, y_scale*1.2, z_scale*1.4))
        bpy.ops.transform.translate(value = Vector((0,0,1.5)))
        
        bpy.ops.object.snap_verts_mesh(influence=1, rest_name = new_name)
        
        for mod in Coping.modifiers:
            if mod.name != 'Multires':
                bpy.ops.object.modifier_apply(modifier = mod.name)
            if mod.name == 'Multires':
                bpy.ops.object.modifier_remove(modifier = 'Multires')
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'DESELECT')
        sce.tool_settings.mesh_select_mode = [True, False, False]
        bpy.ops.mesh.select_non_manifold()        
        bpy.ops.mesh.select_all(action="INVERT")
        bpy.ops.mesh.select_less()
        
        sce.tool_settings.vertex_group_weight = 1
        n = len(Coping.vertex_groups)
        bpy.ops.object.vertex_group_assign(new = True)
        g = Coping.vertex_groups[n]
        g.name = coping
        
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        
        #make margin group active
        bpy.ops.object.vertex_group_set_active(group = margin)
        #select it
        bpy.ops.object.vertex_group_select()
        
        #select more 3 times
        for i in range(0,3):
            bpy.ops.mesh.select_more()
        #deselect it
        bpy.ops.object.vertex_group_deselect()
        
        #select less, now the 3rd loop from bottom is selected.
        bpy.ops.mesh.select_less()
        
        #test which way is up
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode= 'EDIT')
        
        mx = Coping.matrix_world
        vs = Coping.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_i = mx * (svl/n)
            
        bpy.ops.transform.edge_slide(value = .01)
            
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
            
        #establish new COM of loop to test which way to edge slide
        
        vs = Coping.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_f = mx * (svl/n)
        
        if svl_f[2] < svl_i[2]:
            down = 1
            
        else:
            down = -1
        
        #edge slide it completely up (notice the -1)       
        bpy.ops.transform.edge_slide(value = -1*down*.99)        
        
        #deselect all
        bpy.ops.mesh.select_all(action = 'DESELECT')
        
        #selec the margin
        bpy.ops.object.vertex_group_select()
        
        #select more
        bpy.ops.mesh.select_more()
        
        #deselect the margin
        bpy.ops.object.vertex_group_deselect()
        
        #test which way is up
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        vs = Coping.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_i = mx * (svl/n)
            
        bpy.ops.transform.edge_slide(value = .01)
            
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
            
        #establish new COM of loop to test which way to edge slide
        vs = Coping.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_f = mx * (svl/n)
        
        if svl_f[2] < svl_i[2]:
            down = 1
            
        else:
            down = -1        
        #edge slide all the way down
        bpy.ops.transform.edge_slide(value = down*.99)       
        
        #translate them up by the thickness of coping
        bpy.ops.transform.translate(value = (0,0,self.thickness))
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        
        bpy.ops.transform.edge_crease(value = 1, release_confirm = True)
        
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        
        #make margin group active
        bpy.ops.object.vertex_group_set_active(group = margin)
        #select it
        bpy.ops.object.vertex_group_select()
        
        #select more 3 times
        for i in range(0,3):
            bpy.ops.mesh.select_more()
        #deselect it
        bpy.ops.object.vertex_group_deselect()
        
        #select less, now the 3rd loop from bottom is selected.
        bpy.ops.mesh.select_less()
        
        #test which way is up
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode= 'EDIT')
        
        mx = Coping.matrix_world
        vs = Coping.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_i = mx * (svl/n)
            
        bpy.ops.transform.edge_slide(value = .01)
            
        ## ###Toggle for selection and groups to udpate #####
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
            
        #establish new COM of loop to test which way to edge slide
        
        vs = Coping.data.vertices
        sverts = [v for v in vs if v.select]
        svl = Vector((0,0,0))
        for v in sverts:
            svl= svl + v.co
        n = len(sverts)
        svl_f = mx * (svl/n)
        
        if svl_f[2] < svl_i[2]:
            down = 1
            
        else:
            down = -1
        
        #edge slide it a little more than halfway down      
        bpy.ops.transform.edge_slide(value = down*.6)
        
        
        #Apply angle of cervical convergence
        bpy.ops.object.cervical_convergence(ang = self.ang)
        
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.vertex_group_set_active(group = margin)
        bpy.ops.object.vertex_group_select()
        
        #select more
        bpy.ops.mesh.select_more()
        
        #deselect the margin
        bpy.ops.object.vertex_group_deselect()
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode= 'EDIT')
        bpy.ops.transform.edge_crease(value = 1)
        
        
        #Add all the necesary modifiers.
        
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        n = len(Coping.modifiers)
        bpy.ops.object.modifier_add(type = 'SMOOTH')
        mod = Coping.modifiers[n]
        mod.vertex_group = coping
        mod.factor = 1.5
        mod.iterations = 15
        mod.name = 'Collapse Anatomy'
        
        
        n = len(Coping.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Coping.modifiers[n]
        mod.target = Prep
        mod.vertex_group = coping
        mod.wrap_method = 'NEAREST_SURFACEPOINT'
        mod.offset = self.thickness
        mod.name = 'Initial Wrap'
        
        
        n = len(Coping.modifiers)
        bpy.ops.object.modifier_add(type = 'SMOOTH')
        mod = Coping.modifiers[n]
        mod.vertex_group = coping
        mod.factor = 1
        mod.iterations = 2
        mod.name = '2nd Smoothing'
        
        n = len(Coping.modifiers)
        
        
        bpy.ops.object.modifier_add(type = 'MULTIRES')
        mod = Coping.modifiers[n]
        mod.show_only_control_edges = True      
        for i in range(0,3):
            bpy.ops.object.multires_subdivide(modifier = 'Multires')  
        
        n = len(Coping.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Coping.modifiers[n]
        mod.target = Prep
        mod.vertex_group = coping
        mod.wrap_method = 'NEAREST_SURFACEPOINT'
        mod.offset = self.thickness
        mod.name = 'Final Wrap'
        
        #Hide the Min Thickness bubble
        Bubble.hide = True
        
        return {'FINISHED'}

class CopingFromCrown(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.coping_from_crown'
    bl_label = "Coping From Crown"
    bl_options = {'REGISTER','UNDO'}
    
    scale = bpy.props.FloatProperty(name="Initial Shrink", description="", default=.85, min=.5, max=1, step=5, precision=2, options={'ANIMATABLE'})
    cutback = bpy.props.FloatProperty(name="Cutack", description="amount removed", default=.75, min=.2, max=2, step=5, precision=2, options={'ANIMATABLE'})
    smoothing = bpy.props.IntProperty(name="Pre-Smoothing", description="sometimes needed to prevent intersections", default=5, min=0, max=20, options={'ANIMATABLE'})
    auto_groups = bpy.props.BoolProperty(name="Automatic Support", default=True)
        
    def execute(self, context):

        sce=bpy.context.scene
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        contour = tooth.contour
        acoping = str(a + '_Anatomic')
        
        if tooth.rest_type == '1': #what to do if we cutback a pontic!?
            self.auto_groups = False
            
        
        
        bpy.ops.object.select_all(action = 'DESELECT')
        
        Contour = bpy.data.objects[contour]
        sce.objects.active=Contour
        Contour.select=True
        
        #This is going to mess up any contact modifiers...let's hope they dont exist.
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        
        #duplcate the object, and rename it
        current_objects=list(bpy.data.objects)                
        bpy.ops.object.duplicate()
        new_objects = []
        for o in bpy.data.objects:
            if o not in current_objects:
                new_objects.append(o)
                
        bpy.ops.object.select_all(action='DESELECT')
        sce.objects.active=new_objects[0]
        
        new_objects[0].name = acoping
        ACoping = sce.objects[acoping]
        ACoping.select = True
        
        #Clear the higher level multires detail
        bpy.ops.object.multires_base_apply(modifier = 'Multires')
        mod = ACoping.modifiers['Multires']
        subdivs = mod.levels #save these.
        mod.levels = 0
        bpy.ops.object.multires_higher_levels_delete(modifier = 'Multires')
        for i in range(0,subdivs):
            bpy.ops.object.multires_subdivide(modifier = 'Multires')
        
        #Make 3d cursor the pivot point
        for A in bpy.context.window.screen.areas:
            if A.type == 'VIEW_3D':
                for s in A.spaces:
                    if s.type == 'VIEW_3D':
                        s.pivot_point = 'CURSOR'
        
        #Find the BBOX Center of the full contour restoration and put cursor there
        rest_cent = Vector((0,0,0))
        for v in Contour.bound_box:
            rest_cent = rest_cent + Contour.matrix_world * Vector(v)
        Rest_Center = rest_cent/8
        sce.cursor_location = Rest_Center
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'SELECT')
                     
        #Assign the cutback group and support group if required:
        if self.auto_groups:
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.object.vertex_group_set_active(group = a + '_Margin')
            bpy.ops.object.vertex_group_select()
            bpy.ops.mesh.select_more()
            n = len(ACoping.vertex_groups)
            bpy.ops.object.vertex_group_assign(new = True)
            ACoping.vertex_groups[n].name = 'Support'
            bpy.ops.mesh.select_all(action="INVERT")
            
            n = len(ACoping.vertex_groups)
            bpy.ops.object.vertex_group_assign(new = True)
            ACoping.vertex_groups[n].name = 'Cutback'
            
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.object.vertex_group_set_active(group ='Cutback')
            
            #this leaves the 'Cutback' group selected
            bpy.ops.object.vertex_group_select()
        
        if 'Cutback' not in ACoping.vertex_groups:
            n = len(ACoping.vertex_groups)
            bpy.ops.object.vertex_group_add()
            g = ACoping.vertex_groups[n]
            g.name = 'Cutback'
            bpy.ops.object.vertex_group_assign(new = False)
            
        if 'Support' not in ACoping.vertex_groups:
            n = len(ACoping.vertex_groups)
            bpy.ops.object.vertex_group_add()
            g = ACoping.vertex_groups[n]
            g.name = 'Support'
        
        #the cutback group is selected
        #scale it down toward the BBox center
        #the 3d cursor is currently the pivot point    
        scl = self.scale
        bpy.ops.transform.resize(value = (scl, scl, scl))
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        
        #sometimes the scaling results in mesh overlap
        #this initial smoothing reduces anatomical contour
        #but keeps the mesh clean.  Cusps and grooves can be
        #adjusted with sculpting aftward
        n = len(ACoping.modifiers)
        bpy.ops.object.modifier_add(type = 'SMOOTH')
        mod = ACoping.modifiers[n]        
        mod.vertex_group = 'Cutback'
        mod.factor = .5
        mod.iterations = self.smoothing
        mod.name = 'Initial Smoothing'
        
        #if ther dynamic margin modifier is already in place
        #this will not work. Typically, in the design flow
        #that modifier will not be there, but some code to check
        #and then moe up the modiier once or twice might be
        #more robust.
        bpy.ops.object.modifier_move_up(modifier = 'Initial Smoothing')
        
        
        #use a shrinkwrap with offset to 'cutback' the surface
        n = len(ACoping.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = ACoping.modifiers[n]
        mod.target = Contour
        mod.vertex_group = 'Cutback'
        mod.wrap_method = 'NEAREST_SURFACEPOINT'
        mod.offset = -1*self.cutback
        mod.name = 'Cutback'
        mod.use_keep_above_surface = True
        
        bpy.ops.object.modifier_move_up(modifier = 'Cutback')
        
        #use a shrinkwrap w/o offset to pull the suppor out to the
        #surface of the full contour
        n = len(ACoping.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = ACoping.modifiers[n]
        mod.target = Contour
        mod.vertex_group = 'Support'
        mod.wrap_method = 'NEAREST_SURFACEPOINT'
        mod.offset = 0
        mod.name = 'Support'
        mod.use_keep_above_surface = True
        
        bpy.ops.object.modifier_move_up(modifier = 'Support')
        
        #making the full contour crown transparent shows the
        #cutback for good visualization.
        Contour.show_transparent = True
        ACoping.show_transparent = False
        
        #Add in the correct parts for the add on to know what is what.
        if tooth.rest_type == '3' or tooth.rest_type == '1':
            tooth.restoration = acoping
        
        tooth.acoping = acoping
        
        return {'FINISHED'}

          
class AplpyDynamics(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.apply_dynamics'
    bl_label = "Apply Dynamic Properties"
    bl_options = {'REGISTER','UNDO'}
                    
    def execute(self, context):
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        sce=bpy.context.scene
        
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        restoration=tooth.restoration

        Restoration=bpy.data.objects[restoration]
        sce.objects.active=Restoration
        Restoration.select=True
        bpy.ops.object.multires_base_apply(modifier = "Multires")
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        
        if sce.dynamic_margin:
            
            #findout how many modifierst he object has
            n=len(bpy.context.object.modifiers)
            
            #by convention, this will be the name of the object i want to shrinkwrap too
            margin = str(a + "_Margin")
            
            #add a modifier to the active object (which is the tooth)
            bpy.ops.object.modifier_add(type='SHRINKWRAP')
            
            #get the modifier
            mod = bpy.context.object.modifiers[n]
            
            #tell it what to do
            mod.wrap_method='NEAREST_VERTEX'      
            mod.offset=0
            mod.vertex_group=margin #the vertex group in the crown form and the name of the actual margin object are the same.
            
            #rename it
            mod.name='Dynamic Margin'
            mod.show_expanded=False
            
            #lastly, set the target
            mod.target=bpy.data.objects[margin]
        
        if sce.dynamic_ipm:
            n=len(bpy.context.object.modifiers)
            
            sce = bpy.context.scene
            j = sce.working_tooth_index
            tooth = sce.working_teeth[j]
            a = sce.working_teeth[j].name
            mesial = tooth.mesial
            
            
            
            bpy.ops.object.modifier_add(type='SHRINKWRAP')
            mod = bpy.context.object.modifiers[n]
            mod.wrap_method='PROJECT'        
            mod.use_negative_direction=True
            mod.use_positive_direction=False
            mod.use_project_x=True
            mod.offset=sce.i_contact
            mod.target=bpy.data.objects[mesial]
            mod.name='Mesial Contact'
            mod.show_expanded=False
        
        if sce.dynamic_ipd:
            
            n=len(bpy.context.object.modifiers)
            
            sce = bpy.context.scene
            j = sce.working_tooth_index
            tooth = sce.working_teeth[j]
            a = sce.working_teeth[j].name
            distal = tooth.distal
            
            
            
            
            bpy.ops.object.modifier_add(type='SHRINKWRAP')
            mod = bpy.context.object.modifiers[n]
            mod.wrap_method='PROJECT'        
            mod.use_negative_direction=False
            mod.use_positive_direction=True
            mod.use_project_x=True
            mod.offset=sce.i_contact*-1
            mod.target=bpy.data.objects[distal]
            mod.name='Distal Contact'
            mod.show_expanded=False
        
        if sce.dynamic_oc:
            n=len(bpy.context.object.modifiers)
            targ=sce.opposing_model
            
            
            
            bpy.ops.object.modifier_add(type='SHRINKWRAP')
            mod = bpy.context.object.modifiers[n]
            mod.wrap_method='PROJECT'        
            mod.use_negative_direction=True
            mod.use_positive_direction=False
            mod.use_project_z=True
            mod.offset=sce.o_contact
            mod.target=bpy.data.objects[targ]
            mod.name='Safe Occlusion'
            mod.show_expanded=False
        
        return {'FINISHED'}

class CalculateInside(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.calculate_inside'
    bl_label = "calculate_inside"
    bl_options = {'REGISTER','UNDO'}
    
    holy_zone = bpy.props.FloatProperty(name="Holy Zone Width", description="", default=.4, min=.2, max=2, step=5, precision=1, options={'ANIMATABLE'})
    chamfer = bpy.props.FloatProperty(name="Chamfer", description="0 = shoulder 1 = feather", default=.2, min=0, max=1, step=2, precision=2, options={'ANIMATABLE'})
    gap = bpy.props.FloatProperty(name="Gap Thickness", description="thickness required for cement", default=0.07, min=.01, max=.5, step=2, precision=2, options={'ANIMATABLE'})
    
    def invoke(self, context, event): 
        context.window_manager.invoke_props_dialog(self, width=300) 
        return {'RUNNING_MODAL'}
    
    def execute(self, context):
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        v3d = bpy.context.space_data
        v3d.pivot_point = 'MEDIAN_POINT'
            
        sce=bpy.context.scene
        
        master = sce.master_model
        
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        restoration= tooth.restoration
        Restoration=bpy.data.objects[restoration]
        
        margin = tooth.margin
        Margin = bpy.data.objects[margin]
        
                
        bpy.ops.object.select_all(action='DESELECT')
        
        current_objects=list(bpy.data.objects)
        Restoration.hide = False
        sce.objects.active=Restoration
        Restoration.select = True
        
        #we want to make a temporary copy of the resoration so that
        #we can apply all the dynamic modifiers but still have the option
        #to go back and make changes if necessary.        
        bpy.ops.object.duplicate()
        
        inside=str(a + "_Inside")
        for o in bpy.data.objects:
            if o not in current_objects:
                o.name=inside
                o.parent= sce.objects[master]
                
        bpy.ops.object.select_all(action='DESELECT')
        Inside = bpy.data.objects[inside] 
        sce.objects.active=Inside
        Inside.select = True
        
        
        
        bpy.ops.object.multires_base_apply(modifier="Multires")
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        
        #save these for later.  Currently multires level 3 is th
        #all that is needed but I want to keep the option open
        #to let the user define the amount of precision.
        multires_cuts = Restoration.modifiers['Multires'].levels 
        print(multires_cuts)
               
        bpy.ops.object.modifier_remove(modifier="Multires")
        
        for mod in Inside.modifiers:
            bpy.ops.object.modifier_apply(modifier=mod.name)
        
        #clean out the vertex groups
        bpy.ops.object.vertex_group_remove(all = True)
        
        #get the prep and psuedomargin data
        prep=tooth.prep_model
        Prep=bpy.data.objects[prep]
        psuedomargin= tooth.pmargin 
        Psuedomargin=bpy.data.objects[psuedomargin]
         
        sce.objects.active=Inside
        Inside.select=True
        Restoration.hide=False
        
        #Keep just the free edge of the of resoration to use as a starting ppint
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold()        
        bpy.context.tool_settings.mesh_select_mode = [True, False, False]
        bpy.ops.mesh.select_all(action="INVERT")
        bpy.ops.mesh.delete()
        
        
        me = Inside.data
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        bpy.ops.mesh.select_all(action='SELECT')
        
        
        #had to do this further down to keep the vert
        #group from growing through the extrusions
        #6/11/2012
        '''
        #give the margin back it's v.group
        bpy.context.tool_settings.vertex_group_weight = 1
        n = len(Inside.vertex_groups)  #this should be 0
        bpy.ops.object.vertex_group_assign(new = True)
        Inside.vertex_groups[n].name = margin
        '''
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        
        sel_edges=[e for e in me.edges if e.select == True]
        extrude_edges_in(me, sel_edges, Inside.matrix_world, .02)
        
        bpy.ops.mesh.extrude_edges_move()

        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()  #this is to update the selected vertices
               
        sel_edges=[e for e in me.edges if e.select == True]
        sel_verts=[v for v in me.vertices if v.select == True]
        
        extrude_edges_in(me, sel_edges, Inside.matrix_world, self.holy_zone)
        bpy.ops.transform.translate(value = Vector((0,0,self.holy_zone*self.chamfer*2)))
              
        n = len(Inside.vertex_groups)
        bpy.ops.object.vertex_group_assign(new = True)
        Inside.vertex_groups[n].name = 'Holy Zone'
        
        
                
        bpy.ops.object.editmode_toggle()
        
        n = len(Inside.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Inside.modifiers[n]
        mod.target = Prep
        mod.vertex_group = 'Holy Zone'
        mod.wrap_method = 'NEAREST_SURFACEPOINT'
        
        bpy.ops.object.modifier_apply(modifier = mod.name)        
        
        bpy.ops.object.editmode_toggle()  #this is to update the selected vertices 

        sel_edges=[e for e in me.edges if e.select == True]
        
        fill_loop_scale(Inside, sel_edges,.3)  #is this a good scale??.3^3 = 1/27mm
        
        bpy.ops.object.vertex_group_select() #active group is 'filled hole'
        bpy.ops.transform.translate(value = Vector((0,0,10)))
        
        bpy.ops.mesh.select_all(action="INVERT")        
        bpy.ops.transform.translate(value = Vector((0,0,.5)))
        
        #Make normals consistent, very important for projections
        #and upcoming modifiers
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.normals_make_consistent()      
        bpy.ops.object.mode_set(mode='OBJECT')
        
        
        #Project down and then lift off the intaglio
        #Think of this as teasing on/off an acrylic temporary
        n=len(bpy.context.object.modifiers)            
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = bpy.context.object.modifiers[n]
        mod.wrap_method='PROJECT'
        mod.vertex_group = 'filled_hole'       
        mod.use_negative_direction=True
        mod.use_positive_direction=False
        mod.use_project_z=True
        mod.offset = 8            
        mod.target=Prep
        mod.cull_face = 'BACK'
        mod.name = "Initial Projection"
        
              
        #give the margin back it's v.group
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.mesh.select_non_manifold()
        
        bpy.context.tool_settings.vertex_group_weight = 1
        n = len(Inside.vertex_groups)
        bpy.ops.object.vertex_group_assign(new = True)
        Inside.vertex_groups[n].name = margin
        bpy.ops.object.mode_set(mode='OBJECT')
        
        #Subdivide to the same level as the Restoration
        bpy.ops.object.modifier_add(type = 'MULTIRES')        
        for i in range(0,int(multires_cuts)):
            bpy.ops.object.multires_subdivide(modifier = 'Multires')
        
        
        #Apply both modifiers and fix some vertex groups weights
        #note. vertex groups 'grow' during multires subdivision
        for mod in Inside.modifiers:
            bpy.ops.object.modifier_apply(modifier = mod.name)
        
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        bpy.ops.mesh.select_all(action = 'DESELECT')
        
        bpy.ops.object.vertex_group_set_active(group = 'filled_hole')
        bpy.ops.object.vertex_group_select()
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.vertex_group_set_active(group = 'Holy Zone')
        bpy.ops.object.vertex_group_remove_from()
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.vertex_group_select()
        sce.tool_settings.vertex_group_weight = 1
        bpy.ops.object.vertex_group_assign()
        
        bpy.ops.object.mode_set(mode = 'OBJECT')  
           
        #poject the high res mesh onto the prep   
        n=len(bpy.context.object.modifiers)            
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = bpy.context.object.modifiers[n]
        mod.wrap_method='PROJECT'        
        mod.use_negative_direction=True
        mod.use_positive_direction=False
        mod.use_project_z= True         
        mod.target= Prep
        mod.auxiliary_target = Psuedomargin
        mod.name = "Final Seat"
        
        
        #Snap The Edge to the Margin
        n=len(bpy.context.object.modifiers)                    
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = Inside.modifiers[n]
        mod.name = 'Marginal Seal'
        mod.vertex_group = margin
        mod.wrap_method='NEAREST_VERTEX'                  
        mod.target=Margin
        
        #Seal the holy zone to the prep        
        n=len(bpy.context.object.modifiers)                    
        bpy.ops.object.modifier_add(type='SHRINKWRAP')
        mod = Inside.modifiers[n]
        mod.name = 'HZ Seal'
        mod.vertex_group = 'Holy Zone'
        mod.wrap_method='NEAREST_SURFACEPOINT'
        mod.use_keep_above_surface = True                
        mod.target=Prep
        
        
        #Establish the Cement Gap
        n = len(bpy.context.object.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')        
        mod = Inside.modifiers[n]
        
        mod.name = 'Cement Gap'
        mod.offset = self.gap                
        mod.vertex_group = 'filled_hole'
        mod.wrap_method = 'NEAREST_SURFACEPOINT'
        mod.use_keep_above_surface = True
        mod.target = Prep
        
        
        #Apply the "final seat" modifier because it is direction dependent
        #and we do not want further rotations to affect it.
        bpy.ops.object.modifier_apply(modifier="Final Seat")
        
        
        Restoration.hide = True
        tooth.inside = inside
        #for a in bpy.context.window.screen.areas:
        #    if a.type == 'VIEW_3D':
        #        for s in a.spaces:
        #            if s.type == 'VIEW_3D':
        #                if not s.local_view:
        #                    bpy.ops.view3d.localview()
                    
        if tooth.bubble:
            Bubble = sce.objects[tooth.bubble]
            Bubble.hide = True 
        return {'FINISHED'}
    
class HoleFiller(bpy.types.Operator):
    ''''''
    bl_idname = 'object.hole_filler'
    bl_label = "hole_filler"
    
    def execute(self, context):
        
        if bpy.context.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
            
        sce=bpy.context.scene
        ob = bpy.context.object
        me = ob.data
        
        bpy.ops.mesh.select_all(action='SELECT')
        n=len(ob.vertex_groups)
        bpy.context.tool_settings.vertex_group_weight = 1
        bpy.ops.object.vertex_group_assign(new=True)
        bpy.context.object.vertex_groups[n].name='filled_hole'
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()
 
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.remove_doubles(mergedist=.0001)
        
        bpy.ops.object.editmode_toggle()
        bpy.ops.object.editmode_toggle()  #this is to update the selected vertices

        sel_edges=[e for e in me.edges if e.select == True]
        sel_verts=[v for v in me.vertices if v.select == True]

        # Caclulate the average position or COM.
        # There has to be a better way to do this

        L=len(sel_verts)
        COM = Vector((0,0,0))

        for v in sel_verts:
            COM = COM + v.co

        COM = COM*1/L

        R=0

        for v in sel_verts:
            r = v.co - COM
    
            R = R + r.length

        R = R/L



        lengths=[]

        for e in sel_edges:
            v0=me.vertices[e.vertices[0]].co
            v1=me.vertices[e.vertices[1]].co
            V=Vector(v1-v0)
            lengths.append(V.length)
    
        res=min(lengths)

        step = ceil(R/res)
        print(step)

        scl = 1

        for i in range(1,step):
    
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.editmode_toggle()
    
            me = ob.data
    
            sverts=len([v for v in me.vertices if v.select])
    
            if sverts > 4:
                print('extruding again')
                bpy.ops.mesh.extrude_edges_move()
    
                scl = (1 - 1/step*i)/scl
   
    
                bpy.ops.transform.resize(value = (scl, scl, scl))    
                bpy.ops.mesh.remove_doubles(mergedist=.99*res)    
                bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='3', regular=True)
        
        
            if sverts < 3:
                print('break at <3')
                break
                
            if (sverts <= 4 and sverts > 2) or i == step -1:
                print('break at 3 and fill remainder')
                bpy.ops.mesh.fill()
                bpy.ops.mesh.vertices_smooth(repeat=3)
                break
        
        
        ####
        #Now the margin should be filled with a relatively smooth surface.
        #the normals wll be funky just from how we extruded edges with no faces
        #to  begin with. So we will orient them coherently so that things look
        #good
        
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.vertex_group_remove_from()
        bpy.ops.mesh.select_all(action="INVERT")
        bpy.ops.object.vertex_group_assign(new=False)
        
        bpy.ops.object.mode_set(mode='OBJECT')
          
        return {'FINISHED'}

    
    
################################################################################
#################### 80 Character PEP 8 Style Guide  ###########################


class PrepareConnectors(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.prepare_connectors'
    bl_label = "Prepare Connectors"
    bl_options = {'REGISTER','UNDO'}
    def execute(self,context):
        
        sce = bpy.context.scene
        ####  Find out which teeth are in the bridge
        bridge_teeth = [tooth.name for tooth in sce.working_teeth if tooth.in_bridge]
        bridge_teeth.sort()
        
        
        bpy.ops.object.select_all(action='DESELECT')
            
        for a in bridge_teeth:
            tooth = sce.working_teeth[a]
            print(tooth.name)
            if tooth.margin:
                margin = sce.working_teeth[a].margin
                print(margin)
                Margin = bpy.data.objects[margin]
                
                Margin.hide = False
                Margin.select = True
                sce.objects.active = Margin
                
            #bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)    
        current_objects=list(bpy.data.objects)                
        bpy.ops.object.duplicate()
        bpy.ops.object.join()
           
        new_objects = []
        for o in bpy.data.objects:
            if o not in current_objects:
                new_objects.append(o)
                
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.scene.objects.active=new_objects[0]
        
        new_objects[0].name = 'Bridge Margin'
        BridgeMargin = sce.objects['Bridge Margin']
        
        #Duplicate them, rename their vertex groups and join them.
        bpy.ops.object.select_all(action='DESELECT')
        
        for a in bridge_teeth:
            tooth = sce.working_teeth[a]
            restoration = tooth.restoration           
            Restoration = bpy.data.objects[restoration]
           
            Restoration.select = True
            #Change this later since it resets the active objects len(bridge) times
            #but it ends with one of the teeth as the active object, so...
            sce.objects.active = Restoration
            if 'Dynamic Margin' in Restoration.modifiers:
                bpy.ops.object.modifier_apply(modifier = 'Dynamic Margin')
                bpy.ops.object.multires_base_apply()
                    
        current_objects=list(bpy.data.objects)        
        
        bpy.ops.object.duplicate()
        
        
        for tooth in bpy.context.selected_objects:
            
            j = tooth.name.partition('_')
            a = j[0]
            
            for g in tooth.vertex_groups:
                if a not in g.name:
                    new_name = str(a + "_" + g.name)
                    g.name = new_name
        
        
        
        bpy.ops.object.join()
        
        new_objects=[]
        for o in bpy.data.objects:
            if o not in current_objects:
                new_objects.append(o)
                
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.scene.objects.active=new_objects[0]
        
        new_objects[0].name = 'Bridge'
        new_objects[0].select = True
               
        bpy.ops.object.mode_set(mode='EDIT')
        
        Bridge = bpy.data.objects['Bridge']
        
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.vertices_sort()
        
        bpy.ops.mesh.select_all(action = 'DESELECT')   
        for g in Bridge.vertex_groups:
            if 'Margin' in g.name:
                bpy.ops.object.vertex_group_set_active(group = g.name)
                bpy.ops.object.vertex_group_select()
            
        n = len(Bridge.vertex_groups)
        bpy.context.tool_settings.vertex_group_weight = 1
        bpy.ops.object.vertex_group_assign(new = True)
        Bridge.vertex_groups[n].name = 'Bridge Margin'
        
        #remove all the modifiers
        for mod in Bridge.modifiers:
            if mod.name != 'Multires':
                bpy.ops.object.modifier_remove(modifier = mod.name)
                    
        #Add back the maring sealing modifier
        n = len(Bridge.modifiers)
        bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
        mod = Bridge.modifiers[n]
        mod.name = 'Bridge Margin'
        mod.vertex_group = 'Bridge Margin'
        mod.wrap_method = 'NEAREST_VERTEX'
        mod.target = bpy.data.objects['Bridge Margin']
        
        j=len(Bridge.material_slots)
        bpy.ops.object.material_slot_add()
        Bridge.material_slots[j].material=bpy.data.materials["connector_material"]
        
        ####  Determine if the bridge crosses the midline
        midline = floor(int(min(bridge_teeth))/10) != floor(int(max(bridge_teeth))/10)
        print(midline)
        ####  Determine the Begninng, Middle (if necesarry) and End Bridge
        if midline:
            def_end = max(bridge_teeth)
            con_mid = min(bridge_teeth)
            ips_mid = str(int(con_mid)+10)
            con_end = str(max(int(a) for a in bridge_teeth if int(a) < int(ips_mid)))
            
        else:
            def_end = max(bridge_teeth)
            ips_mid = min(bridge_teeth)
            
        if midline:            
                                
            for i in range(int(con_mid),int(con_end)):
                
                                
                Bridge = bpy.data.objects['Bridge']
                bpy.ops.mesh.select_all(action='DESELECT')
                #bpy.ops.object.editmode_toggle()
                #bpy.ops.object.editmode_toggle()  #is this still necessary??
                j = bridge_teeth.index(str(i))
                m_tooth = bridge_teeth[j]
                print(m_tooth)
                d_tooth = bridge_teeth[j+1]
                print(d_tooth)
            
                #mes_dis means mesial tooth, distal connector
                mes_dis = str(m_tooth + "_" + "Distal Connector")
                print(mes_dis)
                bpy.ops.object.vertex_group_set_active(group =mes_dis)
                bpy.ops.object.vertex_group_select()
            
                #bpy.ops.object.editmode_toggle()
                #bpy.ops.object.editmode_toggle()  #is this still necessary??
            
            
                dis_mes = str(d_tooth + "_" + "Mesial Connector")
                print(dis_mes)
                bpy.ops.object.vertex_group_set_active(group =dis_mes)
                bpy.ops.object.vertex_group_select()
            
                #bpy.ops.object.editmode_toggle()
                #bpy.ops.object.editmode_toggle()
                
                bpy.ops.object.material_slot_assign()
                bpy.ops.mesh.region_to_loop()
            
                #bpy.ops.object.editmode_toggle()
                #bpy.ops.object.editmode_toggle()
            
            
                #bpy.ops.mesh.looptools_circle(custom_radius = False, fit = 'inside', flatten = True, influence = 20)
                bpy.ops.mesh.looptools_circle(custom_radius=False, fit='inside', flatten=True, influence=20, radius=1, regular=True)
                #bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='1', regular=True)
                bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='1', regular=True)
                bpy.ops.mesh.loop_to_region()
            
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()
                
            Bridge = bpy.data.objects['Bridge']
            bpy.ops.mesh.select_all(action='DESELECT')
            #bpy.ops.object.editmode_toggle()
            #bpy.ops.object.editmode_toggle()
            
            group1 = ips_mid + '_' + "Mesial Connector"
            group2 = con_mid + '_' + "Mesial Connector"
            
            bpy.ops.object.vertex_group_set_active(group = group1)
            bpy.ops.object.vertex_group_select()
            
            bpy.ops.object.vertex_group_set_active(group = group2)
            bpy.ops.object.vertex_group_select()
            bpy.ops.object.material_slot_assign()
            
            bpy.ops.mesh.looptools_circle(custom_radius=False, fit='inside', flatten=True, influence=20, radius=1, regular=True)                
            bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='1', regular=True)
                
        for i in range(int(ips_mid),int(def_end)):
                
            Bridge = bpy.data.objects['Bridge']
            bpy.ops.mesh.select_all(action='DESELECT')
            #bpy.ops.object.editmode_toggle()
            #bpy.ops.object.editmode_toggle()  #is this still necessary??
                
            j = bridge_teeth.index(str(i))
            m_tooth = bridge_teeth[j]
            print(m_tooth)
            d_tooth = bridge_teeth[j+1]
            print(d_tooth)
           
            #mes_dis means mesial tooth, distal connector
            mes_dis = str(m_tooth + "_" + "Distal Connector")
            print(mes_dis)
            bpy.ops.object.vertex_group_set_active(group =mes_dis)
            bpy.ops.object.vertex_group_select()
            
            #bpy.ops.object.editmode_toggle()
            #bpy.ops.object.editmode_toggle()  #is this still necessary??
           
            
            dis_mes = str(d_tooth + "_" + "Mesial Connector")
            print(dis_mes)
            bpy.ops.object.vertex_group_set_active(group =dis_mes)
            bpy.ops.object.vertex_group_select()
        
            #bpy.ops.object.editmode_toggle()
            #bpy.ops.object.editmode_toggle()
            bpy.ops.object.material_slot_assign()
            bpy.ops.mesh.region_to_loop()
          
            #bpy.ops.object.editmode_toggle()
            #bpy.ops.object.editmode_toggle()
            
            
            #bpy.ops.mesh.looptools_circle(custom_radius = False, fit = 'inside', flatten = True, influence = 20)
            bpy.ops.mesh.looptools_circle(custom_radius=False, fit='inside', flatten=True, influence=20, radius=1, regular=True)
            #bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='1', regular=True)
            bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='1', regular=True)
            bpy.ops.mesh.loop_to_region()
            
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.editmode_toggle()
                
            
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        return {'FINISHED'}


class MakeConnectors(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.make_connectors'
    bl_label = "Make Connectors"
    bl_options = {'REGISTER','UNDO'}
    
    def execute(self,context):

        sce = bpy.context.scene
        ####  Find out which teeth are in the bridge
        bridge_teeth = [tooth.name for tooth in sce.working_teeth if tooth.in_bridge]
        bridge_teeth.sort()
        Bridge = bpy.data.objects['Bridge']
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        bpy.ops.object.select_all(action='DESELECT')
        sce.objects.active = Bridge
        Bridge.select = True
        bpy.ops.object.mode_set(mode = 'EDIT')
        ####  Determine if the bridge crosses the midline
        midline = floor(int(min(bridge_teeth))/10) != floor(int(max(bridge_teeth))/10)
        print(midline)
        ####  Determine the Begninng, Middle (if necesarry) and End Bridge
        if midline:
            def_end = max(bridge_teeth)
            con_mid = min(bridge_teeth)
            ips_mid = str(int(con_mid)+10)
            con_end = str(max(int(a) for a in bridge_teeth if int(a) < int(ips_mid)))
            
        else:
            def_end = max(bridge_teeth)
            ips_mid = min(bridge_teeth)
        
        ####  Iterate through and do everything to the appropriate connectors.
        if midline:            
                                
            for i in range(int(con_mid),int(con_end)):
                
                                
                Bridge = bpy.data.objects['Bridge']
                bpy.ops.mesh.select_all(action='DESELECT')
                #bpy.ops.object.editmode_toggle()
                #bpy.ops.object.editmode_toggle()  #is this still necessary??
                j = bridge_teeth.index(str(i))
                m_tooth = bridge_teeth[j]
                print(m_tooth)
                d_tooth = bridge_teeth[j+1]
                print(d_tooth)
            
                #mes_dis means mesial tooth, distal connector
                mes_dis = str(m_tooth + "_" + "Distal Connector")
                print(mes_dis)
                bpy.ops.object.vertex_group_set_active(group =mes_dis)
                bpy.ops.object.vertex_group_select()
            
                #bpy.ops.object.editmode_toggle()
                #bpy.ops.object.editmode_toggle()  #is this still necessary??
            
            
                dis_mes = str(d_tooth + "_" + "Mesial Connector")
                print(dis_mes)
                bpy.ops.object.vertex_group_set_active(group =dis_mes)
                bpy.ops.object.vertex_group_select()
            
                #bpy.ops.object.editmode_toggle()
                #bpy.ops.object.editmode_toggle()
                bpy.ops.mesh.vertices_sort()
                bpy.ops.mesh.looptools_bridge(cubic_strength=.5, interpolation='cubic', loft=False, loft_loop=False, min_width=0, mode='shortest', remove_faces=True, reverse=False, segments=3, twist=0)
            
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()
                
            Bridge = bpy.data.objects['Bridge']
            bpy.ops.mesh.select_all(action='DESELECT')
            #bpy.ops.object.editmode_toggle()
            #bpy.ops.object.editmode_toggle()
            
            group1 = ips_mid + '_' + "Mesial Connector"
            group2 = con_mid + '_' + "Mesial Connector"
            
            bpy.ops.object.vertex_group_set_active(group = group1)
            bpy.ops.object.vertex_group_select()
            
            bpy.ops.object.vertex_group_set_active(group = group2)
            bpy.ops.object.vertex_group_select()
            bpy.ops.mesh.vertices_sort()
            bpy.ops.mesh.looptools_bridge(cubic_strength=.5, interpolation='cubic', loft=False, loft_loop=False, min_width=0, mode='shortest', remove_faces=True, reverse=False, segments=3, twist=0)
                
        for i in range(int(ips_mid),int(def_end)):
                
            Bridge = bpy.data.objects['Bridge']
            bpy.ops.mesh.select_all(action='DESELECT')
            #bpy.ops.object.editmode_toggle()
            #bpy.ops.object.editmode_toggle()  #is this still necessary??
                
            j = bridge_teeth.index(str(i))
            m_tooth = bridge_teeth[j]
            print(m_tooth)
            d_tooth = bridge_teeth[j+1]
            print(d_tooth)
           
            #mes_dis means mesial tooth, distal connector
            mes_dis = str(m_tooth + "_" + "Distal Connector")
            print(mes_dis)
            bpy.ops.object.vertex_group_set_active(group =mes_dis)
            bpy.ops.object.vertex_group_select()
            
            #bpy.ops.object.editmode_toggle()
            #bpy.ops.object.editmode_toggle()  #is this still necessary??
           
            
            dis_mes = str(d_tooth + "_" + "Mesial Connector")
            print(dis_mes)
            bpy.ops.object.vertex_group_set_active(group =dis_mes)
            bpy.ops.object.vertex_group_select()
        
            #bpy.ops.object.editmode_toggle()
            #bpy.ops.object.editmode_toggle()
            bpy.ops.mesh.vertices_sort()
            bpy.ops.mesh.looptools_bridge(cubic_strength=.5, interpolation='cubic', loft=False, loft_loop=False, min_width=0, mode='shortest', remove_faces=True, reverse=False, segments=3, twist=0)
            
            bpy.ops.object.editmode_toggle()
            bpy.ops.object.editmode_toggle()
            
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside = False)
        bpy.ops.object.editmode_toggle()
        
        return {'FINISHED'}



    
class ManufactureRestoration(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.manufacture_restoration'
    bl_label = "Manufacture Restoration"
    
    
    def execute(self,context):
        
        if  bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        for a in bpy.context.window.screen.areas:
            if a.type == 'VIEW_3D':
                for s in a.spaces:
                    if s.type == 'VIEW_3D':
                        if s.local_view:
                            bpy.ops.view3d.localview()
        
        sce=bpy.context.scene
        
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        a = tooth.name
        restoration=tooth.restoration
        Restoration=sce.objects[restoration]
        
        inside=tooth.inside
        Inside = sce.objects[inside]
        
        
        bpy.ops.object.select_all(action='DESELECT')
        
        sce.objects.active = Restoration
        Restoration.select=True
        Restoration.hide=False
        
        solid_crown=str(a + "_Solid Crown")
                
        current_objects=list(bpy.data.objects)
        
        bpy.ops.object.duplicate()
        
        for o in bpy.data.objects:
            if o not in current_objects:
                sce.objects.active=o
                o.name=solid_crown
                n = len(o.modifiers)
                
                for i in range(0,n):
                    name = o.modifiers[0].name
                    bpy.ops.object.modifier_apply(modifier=name)
                                        
        bpy.ops.object.select_all(action='DESELECT')        
        
        sce.objects.active = Inside
        Inside.select=True
        Inside.hide=False
        
        solid_inside=(a + "_Solid Inside")
        
        current_objects=list(bpy.data.objects)
        
        bpy.ops.object.duplicate()
        
        for o in bpy.data.objects:
            if o not in current_objects:
                sce.objects.active=o
                o.name=solid_inside
                n = len(o.modifiers)
                
                #for mod in o.modifiers:
                    #bpy.ops.object.modifier_apply(modifier =  mod.name)
                for i in range(0,n):
                    name = o.modifiers[0].name
                    bpy.ops.object.modifier_apply(modifier=name)
        
        bpy.ops.object.select_all(action='DESELECT')
        sce.objects.active=bpy.data.objects[solid_crown]
        bpy.data.objects[solid_crown].select = True
        bpy.data.objects[solid_inside].select = True
        
        bpy.ops.object.join()
        
        
        bpy.ops.object.editmode_toggle()
        
        me = bpy.data.objects[solid_crown].data
        
        ### Weld the Two Parts together ###  (boolean modifier may be better depending on code?)
        
        bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False]
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold()
               
        
        #first weld all the very close verts at the resoution of the margin resolution
        bpy.ops.mesh.remove_doubles(mergedist = .025)
        bpy.ops.mesh.select_all(action = 'DESELECT')
        
        #select any remaining non manifold edges and try again after subdividing and using a larger merge
        bpy.context.scene.tool_settings.mesh_select_mode = [False, True, False]        
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.subdivide()
        bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False] 
        bpy.ops.mesh.remove_doubles(mergedist = .03)
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.mesh.select_non_manifold()
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        sel_verts = [v.index for v in me.vertices if v.select]
        
        #if we still have non manifold, it's time to get desperate
        if len(sel_verts):
            
            #repeat
            bpy.context.scene.tool_settings.mesh_select_mode = [False, True, False]        
            bpy.ops.mesh.subdivide()
            bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False]
            bpy.ops.mesh.remove_doubles(mergedist = .05)
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()
        
        
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')        
        sel_verts = [v.index for v in me.vertices if v.select]
        
        if len(sel_verts):
            
            #repeat
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.context.scene.tool_settings.mesh_select_mode = [False, True, False]
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()
        
            bpy.ops.mesh.subdivide()
            bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False]
            bpy.ops.mesh.remove_doubles(mergedist = .1)
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()
            
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')        
        sel_verts = [v.index for v in me.vertices if v.select]
        
        if len(sel_verts):
            
            #repeat
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.context.scene.tool_settings.mesh_select_mode = [False, True, False]
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()
        
            bpy.ops.mesh.subdivide()
            bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False]
            bpy.ops.mesh.remove_doubles(mergedist = .2)
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()    
        
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.normals_make_consistent()
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        for a in bpy.context.window.screen.areas:
            if a.type == 'VIEW_3D':
                for s in a.spaces:
                    if s.type == 'VIEW_3D':
                        if not s.local_view:
                            bpy.ops.view3d.localview()
                
        return {'FINISHED'}
    
    
class BridgeIndividual(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.bridge_individual'
    bl_label = "Bridge Individual"
    bl_options = {'REGISTER','UNDO'}
    
    #properties
    
    #mvert_adj = bpy.props.FloatProperty(name="M. Vertical Adjust", description="", default=0, min=-2, max=2, step=2, precision=1, options={'ANIMATABLE'})
    
    #mlat_adj = bpy.props.FloatProperty(name="M. Lateral Adjust", description="", default=0, min=-2, max=2, step=2, precision=1, options={'ANIMATABLE'})
    
    #dvert_adj = bpy.props.FloatProperty(name="D Vertical Adjust", description="", default=0, min=-2, max=2, step=2, precision=1, options={'ANIMATABLE'})
    
    #dlat_adj = bpy.props.FloatProperty(name="D Lateral Adjust", description="", default=0, min=-2, max=2, step=2, precision=1, options={'ANIMATABLE'})
    
    influence = bpy.props.FloatProperty(name="Nearby Influence", description="", default=0, min=0, max=2, step=2, precision=1, options={'ANIMATABLE'})
    
    mscale = bpy.props.FloatProperty(name="m scale", description="", default=1, min=.75, max=1.5, step=2, precision=1, options={'ANIMATABLE'})
    dscale = bpy.props.FloatProperty(name="d scale", description="", default=1, min=.75, max=1.5, step=2, precision=1, options={'ANIMATABLE'})

    bulbous = bpy.props.FloatProperty(name="bulbous", description="", default=0, min=0, max=1.5, step=2, precision=1, options={'ANIMATABLE'})

    twist = bpy.props.IntProperty(name="twist", description="twist", default=0, min=-5, max=5, options={'ANIMATABLE'})     
    smooth = bpy.props.IntProperty(name="smooth", description="smooth", default=3, min=0, max=20, options={'ANIMATABLE'})     

    
    def execute(self,context):
        
        sce = bpy.context.scene
        j = bpy.context.scene.working_tooth_index
        a = bpy.context.scene.working_teeth[j].name
        
        mid_test = int(a) - (floor(int(a)/10))*10
        #test to see if a midline tooth (eg, 8,9,24,25) or (11,21,31,41)
        if  mid_test == 1:
            if fmod(floor(int(a)/10)*10,20):
                b = str(int(a) + 10)
            else:
                b = str(int(a) - 10)
        else:        
            b = str(int(a)-1)
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
                
        if 'Bridge' not in bpy.data.objects:
            ####  Find out which teeth are in the bridge
            bridge_teeth = [tooth.name for tooth in sce.working_teeth if tooth.in_bridge]
            bridge_teeth.sort()
        
            #Duplicate them, rename their vertex groups and join them.        
            bpy.ops.object.select_all(action='DESELECT')
            
            for a in bridge_teeth:
                tooth = sce.working_teeth[a]
                print(tooth.name)
                if tooth.margin:
                    margin = sce.working_teeth[a].margin
                    print(margin)
                    Margin = bpy.data.objects[margin]
                    
                    Margin.hide = False
                    Margin.select = True
                    sce.objects.active = Margin
                    
            #not sure why this is commented out, I may revisit it    
            #bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)    
            current_objects=list(bpy.data.objects)                
            bpy.ops.object.duplicate()
            bpy.ops.object.join()
            
            new_objects = []
            for o in bpy.data.objects:
                if o not in current_objects:
                    new_objects.append(o)
                
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.scene.objects.active=new_objects[0]
        
            new_objects[0].name = 'Bridge Margin'

            
            #Duplicate them, rename their vertex groups and join them.        
            bpy.ops.object.select_all(action='DESELECT')
            
            for a in bridge_teeth:
            
                ob_name = sce.working_teeth[a].restoration
                ob = bpy.data.objects[ob_name]
                ob.select = True
                ob.hide = False
                
                #test out deleting the fake user...
                me = ob.data
                if me.use_fake_user:
                    me.use_fake_user = False               
                
                #Change this later since it resets the active objects len(bridge) times
                #but it ends with one of the teeth as the active object, so...
                sce.objects.active = ob
                bpy.ops.object.multires_base_apply(modifier = 'Multires')
                
                if 'Dynamic Margin' in ob.modifiers:
                    bpy.ops.object.modifier_apply(modifier = 'Dynamic Margin')
                    bpy.ops.object.multires_base_apply()
                for mod in ob.modifiers:
                    if mod.name != 'Multires':
                        bpy.ops.object.modifier_apply(modifier = mod.name)
        
            
            
            
            
            current_objects=list(bpy.data.objects)                
            bpy.ops.object.duplicate()
        
            #rename their vertex groups
            for tooth in bpy.context.selected_objects:
                j = tooth.name.partition('_')
                a = j[0]
            
                for g in tooth.vertex_groups:
                    if a not in g.name:
                        new_name = str(a + "_" + g.name)
                        g.name = new_name
               
            bpy.ops.object.join()
        
            new_objects=[]
            for o in bpy.data.objects:
                if o not in current_objects:
                    new_objects.append(o)
                
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.scene.objects.active=new_objects[0]
        
            new_objects[0].name = 'Bridge'
            new_objects[0].select = True
            
            Bridge = bpy.data.objects['Bridge']
            
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.select_all(action = 'DESELECT')   
            for g in Bridge.vertex_groups:
                if 'Margin' in g.name:
                    bpy.ops.object.vertex_group_set_active(group = g.name)
                    bpy.ops.object.vertex_group_select()
            
            n = len(Bridge.vertex_groups)
            bpy.context.tool_settings.vertex_group_weight = 1
            bpy.ops.object.vertex_group_assign(new = True)
            Bridge.vertex_groups[n].name = 'Bridge Margin'

        
            Bridge = bpy.data.objects['Bridge']
        
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.sort_elements(type='SELECTED', elements={'VERT'}, reverse=False, seed=0)
        
            j=len(Bridge.material_slots)
            bpy.ops.object.material_slot_add()
            Bridge.material_slots[j].material=bpy.data.materials["connector_material"]
            
            #remove all the modifiers
            for mod in Bridge.modifiers:
                if mod.name != 'Multires':
                    bpy.ops.object.modifier_remove(modifier = mod.name)
                    
            #Add back the maringal modifier
            n = len(Bridge.modifiers)
            bpy.ops.object.modifier_add(type = 'SHRINKWRAP')
            mod = Bridge.modifiers[n]
            mod.name = 'Bridge Margin'
            mod.vertex_group = 'Bridge Margin'
            mod.wrap_method = 'NEAREST_VERTEX'
            mod.target = bpy.data.objects['Bridge Margin'] 
            
            for j in bridge_teeth:
                tooth = sce.working_teeth[j]
                restoration = tooth.restoration
                Restoration = sce.objects[restoration]
                Restoration.hide = True
            
            
        j = sce.working_tooth_index
        a = sce.working_teeth[j].name        
        b = str(int(a)-1)
        
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode = 'OBJECT')
        
        Bridge = bpy.data.objects['Bridge']
        bpy.ops.object.select_all(action = 'DESELECT')
        Bridge.select = True
        sce.objects.active = Bridge
        
        bpy.ops.object.mode_set(mode = 'EDIT')
        dis_mes = str(a + "_" + "Mesial Connector")
        mes_dis = str(b + "_" + "Distal Connector")
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.object.vertex_group_set_active(group = dis_mes)
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.material_slot_assign()
        bpy.ops.mesh.region_to_loop()
        bpy.ops.mesh.looptools_circle(custom_radius=False, fit='inside', flatten=False, influence=20, radius=1, regular=True)
        bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='1', regular=True)
        
        #bpy.ops.transform.translate(value=translate, constraint_axis=(False, False, False), mirror=False, proportional='ENABLED', proportional_edit_falloff='SMOOTH', proportional_size=1.0, snap=False, snap_target='ACTIVE', snap_align=False, release_confirm=True)
        #bpy.ops.transform.translate(value = (0,self.dlat_adj,self.dvert_adj), proportional='ENABLED', proportional_edit_falloff='SMOOTH', proportional_size=self.influence)
        bpy.ops.transform.resize(value = (self.dscale, self.dscale, self.dscale), proportional='ENABLED', proportional_edit_falloff='SMOOTH', proportional_size=self.influence+.01)
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        
        bpy.ops.object.vertex_group_set_active(group=mes_dis)
        bpy.ops.object.vertex_group_select()
        bpy.ops.object.material_slot_assign()
        bpy.ops.mesh.region_to_loop()
        
        #bpy.ops.transform.translate(value = (0,self.mlat_adj,self.mvert_adj), proportional='ENABLED', proportional_edit_falloff='SMOOTH', proportional_size=self.influence)
        bpy.ops.transform.resize(value = (self.mscale, self.mscale, self.mscale), proportional='ENABLED', proportional_edit_falloff='SMOOTH', proportional_size=self.influence+.01)
        
        bpy.ops.object.vertex_group_set_active(group =dis_mes)
        bpy.ops.object.vertex_group_select()
        
        bpy.ops.object.vertex_group_set_active(group =mes_dis)
        bpy.ops.object.vertex_group_select()
        
        bpy.ops.mesh.looptools_relax(input='selected', interpolation='cubic', iterations='1', regular=True)
        bpy.ops.mesh.looptools_bridge(cubic_strength=self.bulbous, interpolation='cubic', loft=False, loft_loop=False, min_width=75, mode='shortest', remove_faces=True, reverse=False, segments=3, twist=self.twist)
        bpy.ops.mesh.vertices_smooth(repeat = self.smooth)
        
        bpy.ops.mesh.select_all(action = 'SELECT')
        bpy.ops.mesh.normals_make_consistent()
        bpy.ops.object.mode_set(mode='OBJECT')

        return{'FINISHED'}
    
    
class StitchBridge(bpy.types.Operator):
    ''''''
    bl_idname = 'view3d.stitch_bridge'
    bl_label = "Stich Bridge"
    
    def execute(self,context):
        sce=bpy.context.scene
    
        #gather a list of the inside objects
        insides = []
        for tooth in sce.working_teeth:
            if tooth.in_bridge and tooth.inside:
                insides.append(tooth.inside)
    
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
            
        bpy.ops.object.select_all(action = 'DESELECT')
    
    
        # apply all the modifiers
        for inside in insides:
            Inside = sce.objects[inside]
            sce.objects.active = Inside
            Inside.hide = False
            Inside.select = True
        
            for mod in Inside.modifiers:
                bpy.ops.object.modifier_apply(modifier = mod.name)
            
        bpy.ops.object.select_all(action = 'DESELECT')
        
        #join all the insides
        for inside in insides:
            Inside = sce.objects[inside]
            sce.objects.active = Inside
            Inside.hide = False
            Inside.select = True
        
        current_objects=list(bpy.data.objects)
        bpy.ops.object.duplicate()
        bpy.ops.object.join() 
    
        for o in bpy.data.objects:
            if o not in current_objects:                
                o.name='Bridge Inside'
                o.data.name = 'Bridge Inside'
    
        BridgeInside = sce.objects['Bridge Inside']
               
        bpy.ops.object.select_all(action = 'DESELECT')            
        current_objects=list(bpy.data.objects)
        Bridge = sce.objects['Bridge']
        Bridge.select = True
        Bridge.hide = False
        sce.objects.active = Bridge
        bpy.ops.object.duplicate()
    
        for o in bpy.data.objects:
            if o not in current_objects:                
                o.name='Solid Bridge'
                o.data.name = 'Solid Bridge'
                
                for mod in o.modifiers:
                    bpy.ops.object.modifier_apply(modifier = mod.name)
    
        SolidBridge = sce.objects['Solid Bridge']
        sce.objects.active = SolidBridge
        BridgeInside.select = True
        bpy.ops.object.join()
    
        bpy.ops.object.mode_set(mode = 'EDIT')    
        me = SolidBridge.data
    
        ### Weld the Two Parts together ###  (boolean modifier may be better depending on code?)
        
        bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False]
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_non_manifold()
               
        
        #first weld all the very close verts at the resoution of the margin resolution
        bpy.ops.mesh.remove_doubles(mergedist = .025)
        bpy.ops.mesh.select_all(action = 'DESELECT')
        
        #select any remaining non manifold edges and try again after subdividing and using a larger merge
        bpy.context.scene.tool_settings.mesh_select_mode = [False, True, False]        
        bpy.ops.mesh.select_non_manifold()
        bpy.ops.mesh.subdivide()
        bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False] 
        bpy.ops.mesh.remove_doubles(mergedist = .03)
        
        bpy.ops.mesh.select_all(action = 'DESELECT')
        bpy.ops.mesh.select_non_manifold()
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')
        
        sel_verts = [v.index for v in me.vertices if v.select]
        
        #if we still have non manifold, it's time to get desperate
        if len(sel_verts):
            
            #repeat
            bpy.context.scene.tool_settings.mesh_select_mode = [False, True, False]        
            bpy.ops.mesh.subdivide()
            bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False]
            bpy.ops.mesh.remove_doubles(mergedist = .05)
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()
        
        
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')        
        sel_verts = [v.index for v in me.vertices if v.select]
        
        if len(sel_verts):
            
            #repeat
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.context.scene.tool_settings.mesh_select_mode = [False, True, False]
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()
        
            bpy.ops.mesh.subdivide()
            bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False]
            bpy.ops.mesh.remove_doubles(mergedist = .1)
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()
            
        bpy.ops.object.mode_set(mode = 'OBJECT')
        bpy.ops.object.mode_set(mode = 'EDIT')        
        sel_verts = [v.index for v in me.vertices if v.select]
        
        if len(sel_verts):
            
            #repeat
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.context.scene.tool_settings.mesh_select_mode = [False, True, False]
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()
        
            bpy.ops.mesh.subdivide()
            bpy.context.scene.tool_settings.mesh_select_mode = [True, False, False]
            bpy.ops.mesh.remove_doubles(mergedist = .2)
            bpy.ops.mesh.select_all(action = 'DESELECT')
            bpy.ops.mesh.select_non_manifold()    
        
        bpy.ops.object.mode_set(mode = 'OBJECT')
        
        for a in bpy.context.window.screen.areas:
            if a.type == 'VIEW_3D':
                for s in a.spaces:
                    if s.type == 'VIEW_3D':
                        if not s.local_view:
                            bpy.ops.view3d.localview()
                
        return {'FINISHED'}
        
##########################################
#######    Panels         ################
##########################################


class View3DPanel():
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'


class VIEW3D_restoration_info(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="TOOLS"
    bl_label = "Restoration Info"
    bl_context = ""
    
    
    def draw(self, context):
        if len(bpy.context.scene.working_teeth):
        
            sce = bpy.context.scene
            layout=self.layout
        
        
            j = bpy.context.scene.working_tooth_index
        
            name = sce.working_teeth[j].name
            mesial = sce.working_teeth[j].mesial
            distal = sce.working_teeth[j].distal
            prep = sce.working_teeth[j].prep_model
            restoration = sce.working_teeth[j].restoration
            
            txt = str("Working on tooth: " + name)        
            row = layout.row()
            row.label(text=txt)
            
            row = layout.row()
            row.prop(sce.working_teeth[j], "rest_type")
            
            row = layout.row()
            row.prop(sce.working_teeth[j], "in_bridge")
        
            if prep:
                txt = str("Prep Model: " + prep)
                row = layout.row()
                row.label(text=txt)
        
            if mesial:
                txt1 = str("Mesial Model: " + mesial)
                row = layout.row()
                row.label(text=txt1)
            
            if distal:
                txt2 = str("Distal Model: " + distal)
                row = layout.row()
                row.label(text=txt2)   
            
            if restoration:
                txt3 = str("Restoration: " + restoration)
                row = layout.row()
                row.label(text=txt3) 

class VIEW3D_PT_DesParams(bpy.types.Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type="TOOLS"
    bl_label = "Design Parameters"
    bl_context = ""
    
    
    
    def draw(self, context):
        
        
        sce=bpy.context.scene
        layout=self.layout
                       
                        
        row=layout.row()
        row.prop(sce, "master_model")
                
        row=layout.row()
        row.prop(sce, "opposing_model")
        
        row=layout.row()
        row.prop(sce, "cement_gap")
        
        row=layout.row()
        row.prop(sce, "i_contact")
        
        row=layout.row()
        row.prop(sce, "o_contact")
        
        row=layout.row()
        row.prop(sce, "holy_zone")
        
        row=layout.row()
        row.prop(sce, "thickness")
        
        row=layout.row()
        row.prop(sce, "coping_thick")


class VIEW3D_PT_DentDesTools(View3DPanel, bpy.types.Panel):
    bl_label = "Dental Design Tools"
    bl_context = ""

    def draw(self, context):
        sce = bpy.context.scene
        layout = self.layout
        
        
        #split = layout.split()

        row = layout.row()
        row.label(text="By Patrick Moore and others...")
        row.operator("wm.url_open", text = "", icon="QUESTION").url = "https://sites.google.com/site/blenderdental/contributors"
        
        row = layout.row()
        row.template_list(sce, "working_teeth", sce, "working_tooth_index")
        
        col = row.column(align=True)
        col.operator("view3d.append_working_tooth", text = "Add a Tooth")
        col.operator("view3d.remove_working_tooth", text = "Remove a Tooth")
        
        j = sce.working_tooth_index
        tooth = sce.working_teeth[j]
        
        row = layout.row()
        row.operator("view3d.slice_view", text = "Slice View", icon = 'MOD_DECIM')
        row.operator("view3d.normal_view", text = "Normal View", icon = 'SPACE2')
        row.operator("object.cursor_to_bound", text = "", icon = 'CURSOR')
        row.operator("view3d.go_to_axis", text = "", icon = "LAMP_HEMI")
        
        row = layout.row()
        row.prop(sce,"design_stage")
        

        
        if sce.design_stage == '0' or sce.design_stage == '1':
        
            row = layout.row(align=True)
            row.label(text="1. Bulk Segmentation")
            row.operator("wm.url_open", text = "", icon="QUESTION").url = "http://www.google.com"
            row.operator("wm.url_open", text = "", icon="CAMERA_DATA").url = "http://www.youtube.com"
            row.separator()
            row.operator("ed.undo", text = "", icon = 'REW')
            
            col=layout.column(align=True)
            col.operator("view3d.split_data",text="Split Data")
            
            col=layout.column(align=True)
            col.operator("object.toss_others",text="Toss Others")
        
            col=layout.column(align=True)
            col.operator("view3d.set_master",text="Make Master")
        
            col=layout.column(align=True)
            col.operator("view3d.set_opposing",text="Make Opposing")
        
            col = layout.column(align=True)
            col.operator("view3d.process_models",text="Process")
        

            
        if sce.design_stage == '0' or sce.design_stage == '2':
        
            row = layout.row(align=True)
            row.label(text="2. Individal Segmentation")
            row.operator("wm.url_open", text = "", icon="QUESTION").url = "http://www.google.com"
            row.operator("wm.url_open", text = "", icon="CAMERA_DATA").url = "http://www.youtube.com"
            row.separator()
            row.operator("ed.undo", text = "", icon = 'REW')
        
            col = layout.column(align=True)
            col.operator("view3d.select_area",text="Select Area")
        
            col = layout.column(align=True)
            col.operator("view3d.define_mesial",text="Define Mesial")
        
            col = layout.column(align=True)
            col.operator("view3d.define_distal", text="Define Distal")
        
            col = layout.column(align=True)
            col.operator("view3d.set_as_prep",text="Define Prep")
            
            col = layout.column(align=True)
            col.operator("view3d.define_axis",text="Define Axis")
            
        if sce.design_stage == '0' or sce.design_stage == '3':
            row = layout.row(align=True)
            row.label(text="3. Margin Marking")
            row.operator("wm.url_open", text = "", icon="QUESTION").url = "http://www.google.com"
            row.operator("wm.url_open", text = "", icon="CAMERA_DATA").url = "http://www.youtube.com"
            row.separator()
            row.operator("ed.undo", text = "", icon = 'REW')
            
            row = layout.row(align=True)
            row.prop(sce, "margin_method",text = "")
        
            if sce.margin_method == '0':
        
                col = layout.column(align=True)        
                col.operator("view3d.initiate_margin",text="Initiate Margin")
        
                col = layout.column(align=True)
                col.operator("curve.cyclic_toggle",text="Close Margin")
               
                col = layout.column(align=True)
                col.operator("view3d.finalize_margin",text="Refine Margin")
        
                col = layout.column(align=True)
                col.operator("view3d.accept_margin",text="Accept Margin")
            
            if sce.margin_method == '1':
            
                col = layout.column(align=True)        
                col.operator("view3d.margin_from_view",text="Auto Margin")
            
                col = layout.column(align=True)
                col.operator("view3d.accept_margin",text="Accept Margin")
                
            if sce.margin_method == '2':
                
                col = layout.column(align=True)        
                col.operator("view3d.initiate_auto_margin",text="Start")
            
                col = layout.column(align=True)
                col.operator("view3d.walk_around_margin",text="Find Margin")
                
                col = layout.column(align=True)
                col.operator("view3d.finalize_margin",text="Adjust Points")
        
                col = layout.column(align=True)
                col.operator("view3d.accept_margin",text="Accept Margin")
        
        if sce.design_stage == '0' or sce.design_stage == '4':
            row = layout.row(align=True)
            row.label(text="4. Restoration Design")
            row.operator("wm.url_open", text = "", icon="QUESTION").url = "http://www.google.com"
            row.operator("wm.url_open", text = "", icon="CAMERA_DATA").url = "http://www.youtube.com"
            row.separator()
            row.operator("ed.undo", text = "", icon = 'REW')
            
            row = layout.row()
            row.prop(sce, "all_functions", text = "Show Unnecessary Functions")
            
            r_type = tooth.rest_type
            
            if r_type != '1' or sce.all_functions:
                col = layout.column(align=True)
                col.operator("view3d.min_thickness", text="Minimum Thickness").thickness = sce.thickness
                        
            if (r_type == '0' or r_type == '1' or r_type == '3') or sce.all_functions:
            
            
            
                col = layout.column(align=True)
                col.operator("view3d.get_crown_form", text="Insert Crown Form")
                
                col = layout.column(align=True)
                col.operator("view3d.auto_rough",text="Auto Rough")
                
                if r_type != '1':
                    row = layout.row(align=False)        
                    row.operator("object.snap_verts_mesh", text="Seat to Margin")
            
                
            if r_type == '2' or sce.all_functions:
                col = layout.column(align=True)
                col.operator("view3d.make_simple_coping",text="Simple Coping").thickness = sce.coping_thick
            
            if r_type != '1' or sce.all_functions:                     
                row = layout.row(align=False)        
                row.operator("object.cervical_convergence", text="Angle Cerv Conv")
            
            if r_type == '3' or sce.all_functions:
                col = layout.column(align=True)
                col.operator("view3d.coping_from_crown",text="Cutback Coping")         
            
            col = layout.column(align=True)
            col.operator("object.editmode_toggle",text="Whole/Structure Editing")
            
            if bpy.context.mode != 'SCULPT':
                col = layout.column(align=True)
                col.operator("view3d.go_to_sculpt", text="Sculpting/Waxing")
            
            if bpy.context.mode == 'SCULPT':
                col = layout.column(align=True)
                col.operator("object.mode_set", text="End Sculpting/Waxing").mode = 'OBJECT'
        
        if sce.design_stage == '0' or sce.design_stage == '5':
            row = layout.row(align=True)
            row.label(text="5. Finalize")
            row.operator("wm.url_open", text = "", icon="QUESTION").url = "http://www.google.com"
            row.operator("wm.url_open", text = "", icon="CAMERA_DATA").url = "http://www.youtube.com"
            row.separator()
            row.operator("ed.undo", text = "", icon = 'REW')
        
            row = layout.row()
            row.label(text="Dynamic Margin")
            row.prop(sce,"dynamic_margin")
        
            row = layout.row()
            row.label(text="Mesial Contact")
            row.prop(sce,"dynamic_ipm")
        
            row = layout.row()
            row.label(text="Distal Contact")
            row.prop(sce,"dynamic_ipd")
        
            row = layout.row()
            row.label(text="Occlusion")
            row.prop(sce,"dynamic_oc")
        
            row=layout.row()
            row.operator("view3d.apply_dynamics",text="Apply Dynamic Props")       
        
            row=layout.row()
            row.operator("view3d.calculate_inside",text="Calculate Inside")
        
            row=layout.row()
            row.operator("view3d.manufacture_restoration",text="Manufacture Restoration")
            
        if sce.design_stage == '0' or sce.design_stage == '6':
            row = layout.row(align=True)
            row.label(text="6. Experimental")
            row.operator("wm.url_open", text = "", icon="QUESTION").url = "http://www.google.com"
            row.operator("wm.url_open", text = "", icon="CAMERA_DATA").url = "http://www.youtube.com"
            
            row=layout.row()
            row.operator("view3d.prepare_connectors",text="Prepare Connectors")
        
            row=layout.row()
            row.operator("view3d.make_connectors",text="Make Connectors")
            
            row=layout.row()
            row.operator("view3d.bridge_individual",text="Bridge Individual")
            
            row=layout.row()
            row.operator("view3d.stitch_bridge",text="Manufacture Bridge")
            
        col = layout.column(align=True)
        col.operator("view3d.go_to_axis",text="Go To Axis")
 
 
classes = ([VIEW3D_PT_DentDesTools, VIEW3D_PT_DesParams, VIEW3D_restoration_info, AddDentalParameters, ManufactureRestoration,
           CalculateInside, AplpyDynamics,TrimCut, AutoRough, GetCrownForm,AcceptMargin,FinalizeMargin,
           InitiateMargin,SetAsIntaglio,SetAsPrep,DefineMesial, DefineDistal, SetOpposing,ProcessModels,
            GoToAxis, SnapVerts2Mesh, SetMaster, SelectArea, GoToSculpt, SplitData, HoleFiller,
           AppendWorkingTooth, RemoveWorkingTooth,PrepareConnectors,MakeConnectors,CervicalConvergence,PrepFromMargin,
           MinThickness, BridgeIndividual, CementGap, SimpleCoping, StitchBridge, MarginFromView, TossOthers,  AddDentalMaterials,
           InitiateAutoMargin, WalkAroundMargin, CopingFromCrown, DefineAxis, CursorToBound, SliceView, NormalView])

    
        
def register():
    
    for c in classes:
        bpy.utils.register_class(c)
       
    bpy.ops.view3d.add_dental_parameters()
    bpy.ops.view3d.add_dental_materials()
    
def unregister():
    
    for c in classes:
        bpy.utils.unregister_class(c)
        
if __name__ == "__main__": 
    register()
    