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
import bgl
import blf
from math import *
from mathutils import *
from mathutils import Vector
from mathutils.geometry import intersect_line_line_2d
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
    
#changes will now be tracked in the commit logs...
    
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

# slightly ugly use of the string representation of GL_LINE_TYPE.
#modified form zeffi's edge filet script
#not very efficient scaling and translating every time
def draw_polyline_2d_loop(context, points, scale, offset, color, LINE_TYPE):
    region = context.region
    rv3d = context.space_data.region_3d

    bgl.glColor4f(*color)  #black or white?

    if LINE_TYPE == "GL_LINE_STIPPLE":
        bgl.glLineStipple(4, 0x5555)
        bgl.glEnable(bgl.GL_LINE_STIPPLE)
        bgl.glColor4f(0.3, 0.3, 0.3, 1.0) #boring grey
    
    bgl.glBegin(bgl.GL_LINE_STRIP)
    for coord in points:
        bgl.glVertex2f(scale*coord[0]+offset[0], scale*coord[1] + offset[1])
    bgl.glVertex2f(scale*points[0][0]+offset[0], scale*points[0][1] + offset[1])
    bgl.glEnd()
    
    if LINE_TYPE == "GL_LINE_STIPPLE":
        bgl.glDisable(bgl.GL_LINE_STIPPLE)
        bgl.glEnable(bgl.GL_BLEND)  # back to uninterupted lines    
    return


def outside_loop(loop, scale, offset):    
    xs = [scale*v[0] + offset[0] for v in loop]
    ys = [scale*v[1] + offset[1]  for v in loop]
    
    maxx = max(xs)
    maxy = max(ys)
    
    bound = (1.1*maxx, 1.1*maxy)
    return bound

def point_inside_loop(loop, point, scale, offset):
        
    nverts = len(loop)
    
    #vectorize our two item tuple
    out = Vector(outside_loop(loop, scale, offset))
    pt = Vector(point)
    
    intersections = 0
    for i in range(0,nverts):
        a = scale*Vector(loop[i-1]) + Vector(offset)
        b = scale*Vector(loop[i]) + Vector(offset)
        if intersect_line_line_2d(pt,out,a,b):
            intersections += 1
    
    inside = False
    if fmod(intersections,2):
        inside = True
    
    return inside

##########################################
### Draw Callbacks For Ops and Menus #####
##########################################

def draw_callback_tooth_select(self, context):
    
    #draw all the buttons
    color = (1.0,1.0,1.0,1.0)
    for i in range(0,len(tooth_button_data)): #each of those is a loop        
        button = tooth_button_data[i]
        
        #check if it's in the rest_type, draw it green.
        #print(len(self.rest_lists))
        #draw it blue if it's in the current type of restoration and selected
        if tooth_button_names[i] in self.rest_lists[self.rest_index]:
            color = (0.5,1.0,1.0,0.5)
        
        #draw it red if the button is hovered
        if self.tooth_button_hover[i]:
            color = (1.0,0.1,0.1,0.5)
        
        draw_polyline_2d_loop(context, button, self.menu_width, self.menu_loc, color,"GL_BLEND")
        color = (1.0,1.0,1.0,1.0)
        
    color = (1.0,1.0,1.0,1.0)
    
    for n in range(0,len(rest_button_data)): #each of those is a loop        
        button = rest_button_data[n]
        
        #draw it red if the button is selected or hovered
        if self.rest_button_select[n]:
            color = (0.1,1.0,0.1,0.5)
        
        draw_polyline_2d_loop(context, button, self.menu_width*.5, self.rest_menu_loc , color,"GL_BLEND")
        color = (1.0,1.0,1.0,1.0)
        
        
##########################################
####### Hard Coded UI Data################
##########################################

#hardcode some button data...easily generated form bezier button data script

tooth_button_data = [

    [(0.40504742345665645,1.6772808403314567),
    (0.4317544069251058,1.6803653284947315),
    (0.45551241603154824,1.6769254662761848),
    (0.47799768603190873,1.667164081753596),
    (0.4858512897677413,1.6571539778842326),
    (0.48581120572723036,1.6442629221279697),
    (0.4804378905228368,1.6324225498081384),
    (0.4639553826386389,1.6070339134353275),
    (0.44812994141143836,1.58394947201316),
    (0.431852704890175,1.5710402863728496),
    (0.41282854306622935,1.5703425691164647),
    (0.39716924522955654,1.5784184409815263),
    (0.38388563499175266,1.5910814567900062),
    (0.37304580564778467,1.5997532069534053),
    (0.3613693813028347,1.6075402754311814),
    (0.35190529855067865,1.6178951303768827),
    (0.34844128676002184,1.6272398108458206),
    (0.34918588676343537,1.6364863349894085),
    (0.3550892886166353,1.6449004425037284),
    (0.3853830501022886,1.66973045182433)],

    [(0.27271350470275735,1.6328630493346012),
    (0.2880053182881735,1.639765152847316),
    (0.3027180732918976,1.641983089209015),
    (0.3214008833927642,1.6394689841946362),
    (0.33046614410580827,1.6330848571347432),
    (0.3341434653134597,1.6221004136375536),
    (0.33473810426425493,1.6104727841758406),
    (0.33363292494589186,1.5879456950484099),
    (0.32976453175714765,1.5704873249094053),
    (0.32105025426808276,1.558557011367933),
    (0.30755337002321403,1.551817510252768),
    (0.29519665010733104,1.5526367543881578),
    (0.28192791204003476,1.5588599787271304),
    (0.27084812730691266,1.5638091537926195),
    (0.25977747833567383,1.568193328018539),
    (0.2492498583425759,1.5749526586943805),
    (0.24341040682255863,1.581990453058012),
    (0.24097887776442664,1.5900860128440313),
    (0.2429579564447949,1.5988700833046925),
    (0.2599006340714486,1.6239553273991485)],

    [(0.1402417173872599,1.5727182921252636),
    (0.152678251284867,1.5819676490632337),
    (0.16669649363085134,1.5858879532090355),
    (0.1828397389778272,1.5873156815777645),
    (0.19903705528757715,1.5878108540358078),
    (0.21337214568523277,1.5859519743620776),
    (0.22658351966628548,1.5780950775027756),
    (0.23660568061673898,1.5635461288342136),
    (0.2400013158329906,1.547140991646585),
    (0.24102229033833691,1.528315514938635),
    (0.24378104255756575,1.5100852083304268),
    (0.24212633653894705,1.4933099665567378),
    (0.2330254357315794,1.4781675474650633),
    (0.21804919544036247,1.4681167929963124),
    (0.20186058997333844,1.4665370852089679),
    (0.18329932445644165,1.4706357137611414),
    (0.16906486907922072,1.4725700874051624),
    (0.15628406213932772,1.4763133419020642),
    (0.14563075460047578,1.4846141376410882),
    (0.13568272433801667,1.5016825736333554),
    (0.13197530469005228,1.519542350736346),
    (0.1314983771983281,1.539994984537546),
    (0.13400716187075756,1.5628348141647934)],

    [(0.07358171900053631,1.4489151211943798),
    (0.08108866837630528,1.458844773703283),
    (0.08983060102052834,1.466225477826904),
    (0.1009399707499816,1.4730672428192735),
    (0.10880443648177418,1.477517704433741),
    (0.11641706679297152,1.480539587841165),
    (0.12561151178233543,1.4813894261558844),
    (0.13883190644299961,1.4786427487227107),
    (0.14999872878352088,1.4729587467944276),
    (0.1622584963116663,1.466075481364356),
    (0.17489286548695415,1.4598062241166692),
    (0.18583602100602017,1.453709908966028),
    (0.19717231527046847,1.4456646312802963),
    (0.20706234406794796,1.4385157913768747),
    (0.2151598336951402,1.4314403208479574),
    (0.21942881941948536,1.4218739742185966),
    (0.21810342574782052,1.4086571471083578),
    (0.21096545669284145,1.3982197162064096),
    (0.1997742900255964,1.3891220554076167),
    (0.18550929358394025,1.381800556686588),
    (0.1705879740938121,1.3788426944322063),
    (0.15325630068356036,1.378036906070133),
    (0.1341836626657459,1.3776533457107563),
    (0.11712780605103293,1.3797088213146247),
    (0.10033084913790631,1.3874988642265023),
    (0.08462741282376272,1.4018629730616126),
    (0.07564388708113329,1.4184597487892106),
    (0.07092785984579825,1.4381837878752575),
    (0.07173550280294382,1.445463502879146)],

    [(0.048974920598543956,1.349719301945641),
    (0.06218571474199652,1.3621183013176814),
    (0.07836274116198251,1.369094907322653),
    (0.09832769170528768,1.3719282682639282),
    (0.11282076350465672,1.3706246162891484),
    (0.12539606891707156,1.365994980429994),
    (0.13893421458261643,1.3596046212224597),
    (0.15791530907946716,1.3515446130059396),
    (0.17395814957055192,1.3429924067654777),
    (0.18721190923755127,1.3296825223597772),
    (0.1918729891143502,1.3203936479401726),
    (0.1929233184514841,1.3113063268408756),
    (0.19128815871410398,1.3013872973109062),
    (0.18855525574361454,1.2935275676572215),
    (0.18416405264663374,1.2872590186081305),
    (0.17717962104718069,1.2819609849144493),
    (0.15886009912089183,1.2743387850697288),
    (0.1401615227487907,1.2719609374651433),
    (0.11878126386962687,1.2724402462746451),
    (0.09968313070237082,1.273780582936677),
    (0.08295998578787057,1.277442536234804),
    (0.06664522801976412,1.2858616011392932),
    (0.05608713778209055,1.2952306436399197),
    (0.049641543510340724,1.3057211894365381),
    (0.04554049823045958,1.3183364726596745),
    (0.04395437239334228,1.3398406397356208)],

    [(0.024027850476330832,1.1980785438983628),
    (0.020665801578475522,1.2182614956743583),
    (0.022915407696121614,1.2382526672706655),
    (0.03460759831230609,1.2570802685744025),
    (0.04433578602572616,1.263448390346035),
    (0.05563916233420274,1.2659505976240077),
    (0.06871099463447498,1.2670522713593226),
    (0.08372798290238623,1.2672682719309807),
    (0.09707294969601638,1.2654671812626515),
    (0.1118119611626723,1.2623918996811194),
    (0.13109570432935258,1.25866436719304),
    (0.14787080446332249,1.2541988917683458),
    (0.16426802753164532,1.2456513596386147),
    (0.17518414756932432,1.2368096418122716),
    (0.18251736697711024,1.2271267256940752),
    (0.18693820818531687,1.21503111860039),
    (0.1899168383635145,1.2004957673448635),
    (0.1879610771219064,1.1876886331221792),
    (0.17724024284696402,1.168570741214106),
    (0.17682978864591933,1.1572115898399846),
    (0.17641936985480441,1.1458524384658633),
    (0.17119507733988992,1.1347717507795319),
    (0.1609132553743598,1.1261356230054913),
    (0.14871352538215635,1.1213542201873001),
    (0.1340412793381006,1.1186139165414866),
    (0.11156453427833465,1.117055737991448),
    (0.09143532592326258,1.119536203572536),
    (0.07012416066958194,1.126030597153764),
    (0.05183295340839341,1.1335382104657163),
    (0.03734896425601294,1.1428089550012737),
    (0.026043388105648782,1.1564920600668553),
    (0.020461388906338116,1.1835491415110393)],

    [(0.023295387226349405,1.0600402270966272),
    (0.021728710293163766,1.0756232165346242),
    (0.022106932605626226,1.08951488608661),
    (0.03011004149123112,1.1019772692329564),
    (0.050820335646475194,1.1123365150099505),
    (0.07421690232092969,1.1136613421227388),
    (0.10047801280607192,1.111635823319464),
    (0.11797685649481496,1.1098561910685818),
    (0.13305962755977496,1.1060135763087173),
    (0.14803200816864587,1.0985499421295517),
    (0.1616382382766752,1.0887484735664519),
    (0.17112466469452242,1.077800289837357),
    (0.17691994232713917,1.0637788783026576),
    (0.1787277608821265,1.051003613016775),
    (0.17648000935955263,1.0395179773734797),
    (0.16892021951606948,1.0290078144757633),
    (0.1655078708129617,1.0180040371569141),
    (0.1610975817638295,1.0109755910147444),
    (0.1532901879863598,1.005140671965739),
    (0.13509187424970784,0.9975052996271405),
    (0.116487081076629,0.9954563394503515),
    (0.09558930019568235,0.9968539693787675),
    (0.07125355595367333,1.0003079247493667),
    (0.05071572143518145,1.0071142798119563),
    (0.03292468385837643,1.0204085130286942),
    (0.02345569683094584,1.0454875957953682)],

    [(0.03633534616357843,0.9394170803195647),
    (0.03405785915247183,0.9545988044332948),
    (0.03289527591169415,0.968198129605017),
    (0.03975668898885033,0.9804217081849274),
    (0.059050462018140785,0.989666815931324),
    (0.08105718009624843,0.9898550551180344),
    (0.10555802756209785,0.9868652531069911),
    (0.12408082019028871,0.984507305882942),
    (0.13995521564541005,0.980090696161344),
    (0.15499607905847546,0.9713421064503224),
    (0.16609700351967618,0.9610541762719051),
    (0.17275750508150198,0.949798492712601),
    (0.1751890872545286,0.936195272448603),
    (0.17355344948309645,0.9257913393402266),
    (0.16854510442494522,0.917090057295391),
    (0.16091472488644565,0.9083707161863676),
    (0.15460954426499715,0.9027620665886562),
    (0.14786386411708563,0.8987341162563234),
    (0.13974226032771322,0.8949451829500055),
    (0.12579474931646442,0.8885388184542107),
    (0.11273490327742271,0.8839893506760782),
    (0.09740070400605991,0.8823885385705846),
    (0.07597234958977242,0.8838053606809414),
    (0.057692469079872265,0.8890297417206804),
    (0.042193772979716555,0.9004626873884631),
    (0.035588479924659,0.9251926990673661)],

    [(0.5929508178029512,1.6808847213447444),
    (0.5662438343345019,1.6839692095080194),
    (0.5424858252280594,1.6805293472894725),
    (0.520000555227699,1.6707679627668837),
    (0.5121469869017962,1.6607578588975203),
    (0.5121870355323773,1.6478668031412573),
    (0.5175603507367709,1.636026430821426),
    (0.5340428586209688,1.6106377944486152),
    (0.5498682998481693,1.5875533530264476),
    (0.5661455363694327,1.5746441673861373),
    (0.5851696981933783,1.5739464501297526),
    (0.6008289606201214,1.5820223219948142),
    (0.6141125708579253,1.594685337803294),
    (0.6249524002018932,1.6033570879666932),
    (0.6366288953667028,1.611144156444469),
    (0.6460929781188588,1.6214990113901704),
    (0.649556919089656,1.6308436918591083),
    (0.6488123190862425,1.6400902160026962),
    (0.6429089880529021,1.6485043235170163),
    (0.6126151557473892,1.6733343328376178)],

    [(0.7240853314153427,1.6356738895605365),
    (0.7087935532398563,1.642575993073251),
    (0.6940807982361322,1.6447939294349503),
    (0.6753979527253359,1.6422798244205714),
    (0.6663327274222215,1.6358956973606784),
    (0.6626554062145701,1.624911253863489),
    (0.6620607318538451,1.6132836244017756),
    (0.6631659465821379,1.5907565352743451),
    (0.6670343397708821,1.5732981651353406),
    (0.6757485818500173,1.5613678515938683),
    (0.6892454306849563,1.5546283504787033),
    (0.7016022214206987,1.5554475946140929),
    (0.7148709594879951,1.5616708189530657),
    (0.7259507265161522,1.5666199940185546),
    (0.7370213577824262,1.571004168244474),
    (0.7475490131854539,1.5777634989203158),
    (0.7533884647054712,1.5848012932839473),
    (0.7558199937636031,1.5928968530699665),
    (0.7538408619683402,1.6016809235306277),
    (0.7368982020466515,1.6267661676250835)],

    [(0.847211181209395,1.5681145763347082),
    (0.8353346199413285,1.5778697287096557),
    (0.821563627430033,1.5823689143875006),
    (0.8055229292396999,1.5844673068262625),
    (0.7893732392855041,1.5856366843473166),
    (0.7749446843781942,1.5843776488840595),
    (0.761284666586829,1.5770816453124723),
    (0.7504153053614245,1.5629699384568339),
    (0.7460554931671937,1.5467283951447888),
    (0.7439246652327534,1.527970763862297),
    (0.740093310830559,1.5098798307377028),
    (0.7407561847160403,1.4930582727758615),
    (0.7489531585409493,1.4775570802756564),
    (0.763319321151987,1.4668957169777794),
    (0.7793963499302743,1.4646436454437723),
    (0.7981784140643142,1.4679633971805055),
    (0.8125108664222012,1.469302034165908),
    (0.825498024727887,1.4725077659287495),
    (0.8366291361542252,1.4803534732502412),
    (0.8475730706917464,1.4969845257898662),
    (0.8523302531179682,1.5146658368467656),
    (0.8540135703598492,1.5350710213420604),
    (0.8528554531964649,1.5579846452629693)],

    [(0.9244164425867293,1.4489151211943798),
    (0.9169095374733726,1.458844773703283),
    (0.9081676048291495,1.466225477826904),
    (0.8970581642798368,1.4730672428192735),
    (0.8891937605154212,1.477517704433741),
    (0.8815811213517415,1.480539587841165),
    (0.8723866498049302,1.4813894261558844),
    (0.8591662817017134,1.4786427487227107),
    (0.847999477066157,1.4729587467944276),
    (0.8357397095380116,1.466075481364356),
    (0.8231053049527939,1.4598062241166692),
    (0.8121621494337279,1.453709908966028),
    (0.8008258728742446,1.4456646312802963),
    (0.7909358086668352,1.4385157913768747),
    (0.7828383367446079,1.4314403208479574),
    (0.7785693864301925,1.4218739742185966),
    (0.7798947801018573,1.4086571471083578),
    (0.7870327137469066,1.3982197162064096),
    (0.7982238804141517,1.3891220554076167),
    (0.8124889122657376,1.381800556686588),
    (0.8274101609360063,1.3788426944322063),
    (0.8447419051661175,1.378036906070133),
    (0.8638144723640724,1.3776533457107563),
    (0.8808703732411977,1.3797088213146247),
    (0.8976673567117716,1.3874988642265023),
    (0.9133707399110205,1.4018629730616126),
    (0.9223543099160622,1.4184597487892106),
    (0.9270703460038796,1.4381837878752575),
    (0.9262626455055982,1.445463502879146)],

    [(0.9508083130900666,1.349719301945641),
    (0.93759757648775,1.3621183013176814),
    (0.9214204792479044,1.369094907322653),
    (0.9014555818194939,1.3719282682639282),
    (0.8869625100201248,1.3706246162891484),
    (0.8743871691977803,1.365994980429994),
    (0.8608490323847178,1.3596046212224597),
    (0.8418679644453144,1.3515446130059396),
    (0.8258251416591945,1.3429924067654777),
    (0.8125713465822654,1.3296825223597772),
    (0.8079102667054665,1.3203936479401726),
    (0.8068599373683326,1.3113063268408756),
    (0.8084950971057127,1.3013872973109062),
    (0.8112279646662723,1.2935275676572215),
    (0.8156192208781479,1.2872590186081305),
    (0.8226036170676712,1.2819609849144493),
    (0.8409231566989248,1.2743387850697288),
    (0.8596217242185435,1.2719609374651433),
    (0.88100195654026,1.2724402462746451),
    (0.9001001605273756,1.273780582936677),
    (0.9168232788844285,1.277442536234804),
    (0.9331380499312587,1.2858616011392932),
    (0.9436960870540376,1.2952306436399197),
    (0.9501416857520286,1.3057211894365381),
    (0.9542427929992869,1.3183364726596745),
    (0.9558288745739919,1.3398406397356208)],

    [(0.9689127728078367,1.2000809046075613),
    (0.9722748040007272,1.2202638563835568),
    (0.9700252111618047,1.240255027979864),
    (0.9583330648080325,1.259082629283601),
    (0.9486048239797177,1.2654507510552335),
    (0.9373014786549297,1.2679529583332063),
    (0.9242296197972102,1.2690546320685212),
    (0.909212693496676,1.2692706326401793),
    (0.8958676824406336,1.26746954197185),
    (0.8811286532690128,1.264394260390318),
    (0.8618449012498501,1.2606667279022385),
    (0.8450698719357397,1.2562012524775443),
    (0.8286725957525223,1.2476537203478133),
    (0.8177564934198082,1.2388121441611895),
    (0.8104232386020924,1.2291290864032738),
    (0.8060024505087805,1.2170334793095885),
    (0.8030238380355477,1.202498128054062),
    (0.8049795284572963,1.1896910646512373),
    (0.8157003804372035,1.1705731019233045),
    (0.8161108523432131,1.1592139505491832),
    (0.8165212534293631,1.1478547991750618),
    (0.8217455636492426,1.1367741114887304),
    (0.8320274033197376,1.1281379837146899),
    (0.844227115606976,1.1233565808964987),
    (0.8588993616510319,1.1206162772506851),
    (0.8813760978583154,1.1190580987006467),
    (0.901505297360905,1.1215385642817346),
    (0.9228164803195505,1.1280329578629626),
    (0.9411076920069803,1.135540571174915),
    (0.9555916988643256,1.1448113157104722),
    (0.96689723960476,1.158494420776054),
    (0.9724792609352768,1.1855515022202379)],

    [(0.9693478900249731,1.0603167078283493),
    (0.9709145669581588,1.0758996972663464),
    (0.970536318088249,1.089791366818332),
    (0.9625332490388151,1.1022537499646785),
    (0.9418229017686763,1.1126129957416726),
    (0.918426357225428,1.113937822854461),
    (0.8921652201828384,1.1119123040511862),
    (0.8746664119040252,1.1101326718003037),
    (0.8595836231341003,1.1062900570404395),
    (0.8446112425252293,1.0988264228612739),
    (0.8310050478271298,1.089024954298174),
    (0.8215185859993528,1.0780767705690792),
    (0.815723326071701,1.0640553590343798),
    (0.8139155075167136,1.0512800937484972),
    (0.8161632590392875,1.0397944581052019),
    (0.8237230665877355,1.0292842952074854),
    (0.8271353798809136,1.0182805178886363),
    (0.8315456866350106,1.0112520717464666),
    (0.8393530804124804,1.0054171526974611),
    (0.8575513764441675,0.9977817803588626),
    (0.8761561784697287,0.9957328201820735),
    (0.8970539859081227,0.9971304501104896),
    (0.9213897434288554,1.0005844054810888),
    (0.941927573521106,1.0073907605436783),
    (0.9597185845404637,1.0206849937604163),
    (0.9691875538629294,1.0457640765270904)],

    [(0.9616628729648231,0.9381918967491772),
    (0.9639403688284122,0.9533736208629073),
    (0.9651029476429486,0.9669729460346296),
    (0.9582414947296214,0.9791965246145399),
    (0.9389477571102608,0.9884416323609365),
    (0.9169410523108767,0.9886298715476469),
    (0.8924401428776503,0.9856400695366037),
    (0.8739173502494594,0.9832821223125545),
    (0.8580430079092327,0.9788655125909566),
    (0.8430021444961673,0.9701169228799349),
    (0.8319012023300016,0.9598289927015177),
    (0.8252406653582461,0.9485733091422135),
    (0.8228091363001141,0.9349700888782155),
    (0.8244447917765112,0.9245661557698391),
    (0.8294531014247326,0.9158648737250035),
    (0.837083516373162,0.9071455326159801),
    (0.8433886792896457,0.9015368830182687),
    (0.8501343417325923,0.8975089326859359),
    (0.8582559632269295,0.893719999379618),
    (0.8722034388282486,0.8873136348838232),
    (0.8852633291297025,0.8827641671056907),
    (0.9005975284010653,0.8811633550001972),
    (0.922025847407423,0.8825801771105539),
    (0.9403057279173231,0.8878045581502929),
    (0.9558044417224437,0.8992375038180757),
    (0.9624097392037425,0.9239675154969786)],

    [(0.549915501284566,0.028264907509617514),
    (0.5607402459984477,0.028074835859041),
    (0.5702375432647374,0.02945633656444221),
    (0.5794759231244758,0.03368595751247509),
    (0.5865153109349475,0.0394024347726077),
    (0.5908378364731199,0.04607999064186376),
    (0.5927406244597773,0.05438292425539822),
    (0.5916234411752187,0.0674776225178259),
    (0.5863327019270721,0.07871935456479673),
    (0.5776908023344776,0.09003279171957206),
    (0.570385521361288,0.09852152566090332),
    (0.5623760431145639,0.10487624477411403),
    (0.5517108555442708,0.10766389149604333),
    (0.5397235674257823,0.10561221360714368),
    (0.5304670576819965,0.09937931350485855),
    (0.5220474970384905,0.09059504828958354),
    (0.5145436371790948,0.08094653291816843),
    (0.5102094971839545,0.07110846819264106),
    (0.508849295551316,0.05946680754625262),
    (0.5096318195895239,0.050979928199993585),
    (0.512508663924569,0.04369368449030203),
    (0.5184045588726555,0.03707854526164503),
    (0.538143328489491,0.02906384626339903)],

    [(0.663248664178104,0.040618562253453935),
    (0.6723815932669577,0.042645293846823584),
    (0.6802041424943731,0.045395720306312885),
    (0.6873228839574818,0.050524658306571095),
    (0.6952695095788464,0.060116615167645125),
    (0.6993674299324244,0.07022052879347816),
    (0.6993045418971351,0.08171253822413395),
    (0.6943091922832131,0.0936736052896203),
    (0.6853532420233999,0.10248471123166854),
    (0.6736761802997139,0.11087875902076813),
    (0.6670162807066944,0.11589023785770491),
    (0.6604019891032314,0.11951322252810893),
    (0.6522876620544289,0.12018965841669597),
    (0.6390569542517163,0.11541447889366348),
    (0.6296090892473994,0.10651529960376996),
    (0.6214388145095445,0.09491395316243603),
    (0.6138686672616007,0.08245464182749797),
    (0.6098278985346876,0.07038001511720722),
    (0.6107414039031516,0.057002860697407065),
    (0.6142884165692126,0.04902973074360215),
    (0.6201819036420742,0.04320531073877649),
    (0.6286368742153602,0.03898162316710236),
    (0.6511341481819161,0.03788430485315042)],

    [(0.8026107457947345,0.08560727640063445),
    (0.8063133496922488,0.09606588244059117),
    (0.8056492010492954,0.10663976550694661),
    (0.8032536484798198,0.11834508435459702),
    (0.8006201411822228,0.13275588118212225),
    (0.7964911309102979,0.14514921496539776),
    (0.787684468914437,0.15604637298567958),
    (0.772352889977878,0.16508551887551093),
    (0.756148031353085,0.1680237640287945),
    (0.7378189310407905,0.16744036773070436),
    (0.7251071203490739,0.16611161011571043),
    (0.7142887494225525,0.16261029396403046),
    (0.7054357712385395,0.15459858489173023),
    (0.7006726399441147,0.14350266208311094),
    (0.7008270272379553,0.13200996215882443),
    (0.7038884989468732,0.11948120309910538),
    (0.7104165319613921,0.10137842535299982),
    (0.719874524205626,0.08684674787768815),
    (0.7346200688043263,0.07503547366765359),
    (0.7473178571638501,0.0699367005013267),
    (0.7598488647541103,0.06920473741660342),
    (0.7736981840300792,0.07116251259796777),
    (0.7949038453979803,0.07763474841563581)],

    [(0.8761497338625087,0.19621245830392242),
    (0.8766746506615672,0.20749227373037166),
    (0.8735310987354193,0.21763672287332034),
    (0.8670638999802625,0.2278765309571665),
    (0.8567983488774662,0.2394718488579554),
    (0.8450423938302305,0.2475852729535486),
    (0.830055141050852,0.25265590407818284),
    (0.8113599020646326,0.2544891469627522),
    (0.7948264392914812,0.25140559716261646),
    (0.7783849715158984,0.24373534604318467),
    (0.7702003911664123,0.23825548236008315),
    (0.7645509493295944,0.23172713065619627),
    (0.7620583027326622,0.22302147548503282),
    (0.7641809863832532,0.2097492672446181),
    (0.7714154474968826,0.19865175984164113),
    (0.7818804273241997,0.18705484849401213),
    (0.7883065505608118,0.17595098500863968),
    (0.8012285545957025,0.16678418632195147),
    (0.817628097014426,0.16102495599785074),
    (0.8310008694554158,0.16020459644967297),
    (0.8426698577151119,0.16330147808837087),
    (0.8542839605836491,0.16942872381267496),
    (0.8719617306475704,0.1850789567073241)],

    [(0.927689099116855,0.31514154092541585),
    (0.9250009897075373,0.32789042581361216),
    (0.9172514557553281,0.3380096630865575),
    (0.9055729068145913,0.3468618976620452),
    (0.8897453055816743,0.3546461687553686),
    (0.8735997231793329,0.3579095124739622),
    (0.8550802590845414,0.35859409264639863),
    (0.834382730208983,0.3592713429633706),
    (0.8160883316278731,0.35731250105787166),
    (0.8035976205377026,0.3468618976620452),
    (0.8000006090507922,0.3361451886439222),
    (0.8002159014238545,0.3270185271126396),
    (0.80211252808273,0.3173141525769966),
    (0.79774131389111,0.30910949479732525),
    (0.7933455960280823,0.30124144381014245),
    (0.791551941445007,0.29312571806911353),
    (0.7961579942909278,0.2811292410738472),
    (0.8069668753562681,0.2729660483219482),
    (0.8214185175377946,0.2673437304913418),
    (0.8478637153953805,0.26216061972476146),
    (0.8724639850915697,0.2642185563187497),
    (0.8971574537229398,0.2738616008560138),
    (0.9238003098085577,0.29811871292270514)],

    [(0.949085195087113,0.44322279793259833),
    (0.9546546813024877,0.45517410956243026),
    (0.9565993238261449,0.468662141324854),
    (0.9543684982500058,0.4834788598824121),
    (0.9494531750773866,0.4950136090983123),
    (0.9419997389579976,0.5041055334884808),
    (0.9313502733965268,0.5121832466698908),
    (0.9222262676099777,0.5240325777019564),
    (0.9128710349819653,0.5322964408842199),
    (0.8999481102889004,0.5380212350516096),
    (0.8842780832435042,0.5416535856484405),
    (0.8698925159909472,0.5407467727567048),
    (0.8513739017344704,0.5341021702533503),
    (0.8317187703717752,0.5313448698412424),
    (0.8121680274820714,0.5237193414631227),
    (0.7967403459960894,0.5094214137867712),
    (0.7924298952439719,0.4931075633981153),
    (0.7961187600887316,0.47686386008035364),
    (0.7990730813501353,0.4586921214960015),
    (0.7964909184507193,0.4437247336872296),
    (0.7933449586493463,0.43040978566157045),
    (0.7957174239446052,0.41619489427055295),
    (0.8056054343760872,0.4014088761221141),
    (0.8192423648932359,0.3911146429761961),
    (0.837087694744876,0.3833102236328279),
    (0.8618817983966809,0.37674717019775666),
    (0.8852022824107618,0.3760168403960445),
    (0.9103553719306761,0.38083375937380515),
    (0.9226205925880077,0.3852803613059267),
    (0.9321823359264969,0.3915806022421709),
    (0.9402169198134349,0.40076852295197285),
    (0.9503229845925022,0.42755135449001097)],

    [(0.9528530948951416,0.6324195753740368),
    (0.9521388766114793,0.6444267284631319),
    (0.9507469830916877,0.6562833893506619),
    (0.9465327057088526,0.6673970082716888),
    (0.9387698576230461,0.6767576232090277),
    (0.9295027957201859,0.6817476613334827),
    (0.9166602515677215,0.6861522316789554),
    (0.8903212834994755,0.6912807226288502),
    (0.8652183344401296,0.6909886615280249),
    (0.8384016155992922,0.6848346990117018),
    (0.824678993052076,0.6777491720627268),
    (0.8152247542603988,0.6685510178832185),
    (0.80857923109887,0.6558459350781599),
    (0.8060288663163964,0.6442962782818223),
    (0.8072553246442559,0.6335849161630961),
    (0.8112812212006615,0.6223773192884332),
    (0.8114762590938897,0.6074424023852695),
    (0.8126706360253685,0.5941513560622118),
    (0.8196434177579239,0.5814599414900484),
    (0.832218050381673,0.5717199445650467),
    (0.8468495750064817,0.5668935003161752),
    (0.8641209098963883,0.5644000747007879),
    (0.8877437238909309,0.5628790057571589),
    (0.9088019383112281,0.5653057898847003),
    (0.9304706199209324,0.5730966472249628),
    (0.940374635640675,0.5788712631635529),
    (0.9475415346082844,0.5858931584687131),
    (0.9528511827589334,0.5951975778474913),
    (0.9558730661663574,0.6201173159301554)],

    [(0.9512442093256582,0.7817224282175215),
    (0.9507687247885726,0.7915629893430983),
    (0.9498258291783912,0.8002835343897343),
    (0.9461477997721441,0.8093064802366913),
    (0.9388666683710646,0.8194864101292795),
    (0.9300566070219448,0.8270513875274754),
    (0.918127639057804,0.8326965093528601),
    (0.8938407472401677,0.8389518150882136),
    (0.8709393043351031,0.8391757474841421),
    (0.8469783963310213,0.8326965093528601),
    (0.8343034119662759,0.8259006356294855),
    (0.8254323038982154,0.8169038223107061),
    (0.8192329458519144,0.8049660726839799),
    (0.8176181822340876,0.7946270813868199),
    (0.8194592153032084,0.7850552108084137),
    (0.8217052671491529,0.7743420781931984),
    (0.8216903949786453,0.7598933396259139),
    (0.8218380543858278,0.7469927940084699),
    (0.8280235317396551,0.7347961269751924),
    (0.8399381940921647,0.7263377570486474),
    (0.8538713640818527,0.7228319615408503),
    (0.8700537728111652,0.7212926210734548),
    (0.8917066615921876,0.7201845027309199),
    (0.9109560659794638,0.7222632072487242),
    (0.9307641682388085,0.7292500821333321),
    (0.9398263482879617,0.7345338810352419),
    (0.9463841256434957,0.7409589419739605),
    (0.9512424388291693,0.7494725513909622),
    (0.9528883631852024,0.7703988284128993)],

    [(0.44893208255074435,0.02826489644401446),
    (0.43810730242693285,0.028074824793437946),
    (0.42861004057057295,0.029456327711959766),
    (0.4193716607108345,0.03368595087311326),
    (0.41233223749043313,0.03940243034636648),
    (0.40800974736219037,0.04607999064186376),
    (0.40610695937553315,0.05438292868163945),
    (0.40722414266009166,0.06747763137030834),
    (0.41251488190823826,0.07871937226976163),
    (0.42115678150083286,0.09003280942453694),
    (0.42846206247402235,0.09852154336586821),
    (0.43647154072074645,0.10487627133156137),
    (0.44713672829103956,0.10766391805349067),
    (0.459124016409528,0.10561224016459102),
    (0.46838052615331377,0.09937933120982345),
    (0.47680008679681984,0.09059506599454843),
    (0.4843039466562155,0.08094655062313331),
    (0.4886380866513559,0.0711084770451235),
    (0.48999828828399444,0.05946680754625262),
    (0.4892157996557163,0.05097992377375236),
    (0.48633895532067123,0.04369367563781959),
    (0.48044306037258466,0.03707853640916259),
    (0.4607042553458194,0.02906383519779597)],

    [(0.33559899047706593,0.040618562253453935),
    (0.3264660967981421,0.042645293846823584),
    (0.3186435121607968,0.04539572473255411),
    (0.311524806107618,0.050524658306571095),
    (0.30357814507632364,0.060116615167645125),
    (0.29948022472274555,0.07022052879347816),
    (0.29954307734810504,0.08171253822413395),
    (0.3045384623719568,0.0936736052896203),
    (0.3134944126317701,0.10248471123166854),
    (0.32517147435545607,0.11087875902076813),
    (0.3318313385385458,0.11589023785770491),
    (0.33844566555193845,0.11951322252810893),
    (0.34655999260074105,0.12018965841669597),
    (0.3597907004034536,0.11541447889366348),
    (0.36923856540777045,0.10651529960376996),
    (0.37740887555555525,0.09491394430995359),
    (0.38497895198363946,0.08245464182749797),
    (0.3890197561204824,0.07038001511720722),
    (0.3881062153420886,0.057002860697407065),
    (0.3845592380859573,0.04902973074360215),
    (0.37866571560316603,0.04320530631253526),
    (0.3702107804398097,0.03898161874086114),
    (0.34771350647325383,0.03788430485315042)],

    [(0.19623690886043552,0.08560727640063445),
    (0.1925342695529914,0.09606588244059117),
    (0.1931984536058746,0.10663976550694661),
    (0.1955940061753501,0.11834508435459702),
    (0.198227531177912,0.13275588118212225),
    (0.20235648833494224,0.14514921496539776),
    (0.2111631503308031,0.15604637298567958),
    (0.22649480008722173,0.16508551887551093),
    (0.24269958789215523,0.1680237640287945),
    (0.26102870590941446,0.16744036773070436),
    (0.2737405520110609,0.16611161011571043),
    (0.2845589052326174,0.16261029396403046),
    (0.29341188341663044,0.15459858489173023),
    (0.29817501471105534,0.14350266208311094),
    (0.2980206274172146,0.13200996215882443),
    (0.29495919111822644,0.11948120309910538),
    (0.2884311226937778,0.10137842535299982),
    (0.27897311274457903,0.08684674787768815),
    (0.2642275681458787,0.07503547366765359),
    (0.25152976208139,0.0699367005013267),
    (0.23899875449112992,0.06920473741660342),
    (0.22514950603502057,0.07116251259796777),
    (0.2039438092571896,0.07763474841563581)],

    [(0.12269784997280163,0.19621245830392242),
    (0.12217293317374314,0.20749227373037166),
    (0.12531646739492616,0.21763672287332034),
    (0.13178371926497767,0.2278765309571665),
    (0.14204922610536166,0.2394718488579554),
    (0.1538052077100448,0.2475852729535486),
    (0.1687924781943882,0.25265590407818284),
    (0.18748769947564267,0.2544891469627522),
    (0.2040211445438291,0.25140559716261646),
    (0.22046259461444712,0.24373534604318467),
    (0.22864722807882787,0.23825548236008315),
    (0.23429663450571597,0.23172713065619627),
    (0.23678931651257798,0.22302147548503282),
    (0.23466661515702214,0.2097492672446181),
    (0.2274321363384277,0.19865175984164113),
    (0.2169671565111106,0.18705484849401213),
    (0.21054106868442832,0.17595098500863968),
    (0.19761904694457277,0.16678418632195147),
    (0.18121948682088446,0.16102495599785074),
    (0.16784671437989457,0.16020459644967297),
    (0.15617774382516333,0.16330147808837087),
    (0.14456361439917884,0.16942872381267496),
    (0.12688588859766975,0.1850789567073241)],

    [(0.07115858652200341,0.31514154092541585),
    (0.07384665166890894,0.32789042581361216),
    (0.08159625201473648,0.3380096630865575),
    (0.09327477439802588,0.3468618976620452),
    (0.10910239333590786,0.3546461687553686),
    (0.12524792262335455,0.3579095124739622),
    (0.1437673867181461,0.35859409264639863),
    (0.1644649598561167,0.3592713429633706),
    (0.18275935843722665,0.35731250105787166),
    (0.1952500518224322,0.3468618976620452),
    (0.19884706330934263,0.3361451886439222),
    (0.19863175323131543,0.3270185271126396),
    (0.19673512657243988,0.3173141525769966),
    (0.20110637617398966,0.30910949479732525),
    (0.20550209403701739,0.30124144381014245),
    (0.20729571321016296,0.29312571806911353),
    (0.20268964265927722,0.2811292410738472),
    (0.1918807792989018,0.2729660483219482),
    (0.17742913711737535,0.2673437304913418),
    (0.1509839392597894,0.26216061972476146),
    (0.12638366071111778,0.2642185563187497),
    (0.10169021863719503,0.2738616008560138),
    (0.07504738910902455,0.29811871292270514)],

    [(0.0497624153056447,0.44322279793259833),
    (0.04419296450019982,0.45517410956243026),
    (0.04224832197654262,0.468662141324854),
    (0.044479156405164096,0.4834788598824121),
    (0.049394444167853546,0.4950136090983123),
    (0.0568479156971723,0.5041055334884808),
    (0.06749736355367823,0.5121832466698908),
    (0.07662136934022731,0.5240325777019564),
    (0.0859766019682397,0.5322964408842199),
    (0.09889950010385733,0.5380212350516096),
    (0.11456953600173593,0.5416535856484405),
    (0.12895508554932805,0.5407467727567048),
    (0.1474737086582873,0.5341021702533503),
    (0.16712886657842985,0.5313448698412424),
    (0.18667962717309852,0.5237193414631227),
    (0.2021072732491507,0.5094214137867712),
    (0.20641775941119803,0.4931075633981153),
    (0.20272884145154366,0.47686386008035364),
    (0.19977459100999956,0.4586921214960015),
    (0.20235670079452092,0.4437247336872296),
    (0.20550269600582366,0.43040978566157045),
    (0.2031301953006349,0.41619489427055295),
    (0.19324218486915287,0.4014088761221141),
    (0.17960528976193407,0.3911146429761961),
    (0.1617599599102939,0.3833102236328279),
    (0.1369658385535242,0.37674717019775666),
    (0.11364534568696077,0.3760168403960445),
    (0.0884922384620816,0.38083375937380515),
    (0.0762270443621974,0.3852803613059267),
    (0.06666528331874326,0.3915806022421709),
    (0.05863069943180518,0.40076852295197285),
    (0.048524634652738007,0.42755135449001097)],

    [(0.04599455976002832,0.6324195753740368),
    (0.04670883115858528,0.6444267284631319),
    (0.0481006627109998,0.6562833893506619),
    (0.052314940093834895,0.6673970082716888),
    (0.06007780588460626,0.6767576232090277),
    (0.06934485008250159,0.6817476613334827),
    (0.08218739423496599,0.6861522316789554),
    (0.10852642427058909,0.6912807226288502),
    (0.13362931136255782,0.6909886615280249),
    (0.1604460390558778,0.6848346990117018),
    (0.1741686970130237,0.6777491720627268),
    (0.1836229358047009,0.6685510178832185),
    (0.19026844126126485,0.6558459350781599),
    (0.1928188060437385,0.6442962782818223),
    (0.19159233001091405,0.6335849161630961),
    (0.18756641574954358,0.6223773192884332),
    (0.18737139556128032,0.6074424023852695),
    (0.1861770540397312,0.5941513560622118),
    (0.17920427230717575,0.5814599414900484),
    (0.1666296573883916,0.5717199445650467),
    (0.15199807964868817,0.5668935003161752),
    (0.1347267978736762,0.5644000747007879),
    (0.11110396617416883,0.5628790057571589),
    (0.09004575175387153,0.5653057898847003),
    (0.0683770347342375,0.5730966472249628),
    (0.058473041145701024,0.5788712631635529),
    (0.051306111194403134,0.5858931584687131),
    (0.045996498453683775,0.5951975778474913),
    (0.042974597341294996,0.6201173159301554)],

    [(0.047603454181994145,0.7817224282175215),
    (0.04807897412900956,0.7915629893430983),
    (0.04902186088670855,0.8002835343897343),
    (0.052699907997920445,0.8093064802366913),
    (0.05998100841531145,0.8194864101292795),
    (0.06879103878074264,0.8270513875274754),
    (0.08072006871226053,0.8326965093528601),
    (0.10500691626748462,0.8389518150882136),
    (0.1279083503200668,0.8391757474841421),
    (0.15186929373407837,0.8326965093528601),
    (0.16454427809882388,0.8259006356294855),
    (0.1734153861668843,0.8169038223107061),
    (0.17961474421318532,0.8049660726839799),
    (0.1812295078310122,0.7946270813868199),
    (0.17938847476189124,0.7850552108084137),
    (0.17714236980105214,0.7743420781931984),
    (0.1771572950864544,0.7598933396259139),
    (0.17700963567927186,0.7469927940084699),
    (0.17082410521054991,0.7347961269751924),
    (0.15890946056300512,0.7263377570486474),
    (0.144976325983247,0.7228319615408503),
    (0.1287938641390398,0.7212926210734548),
    (0.10714101962042963,0.7201845027309199),
    (0.08789157982322371,0.7222632072487242),
    (0.06808352625253243,0.7292500821333321),
    (0.05902132407217309,0.7345338810352419),
    (0.052463542290397826,0.7409589419739605),
    (0.047605224678483146,0.7494725513909622),
    (0.04595928261748501,0.7703988284128993)]]

tooth_button_names = [
    '11',
    '12',
    '13',
    '14',
    '15',
    '16',
    '17',
    '18',
    '21',
    '22',
    '23',
    '24',
    '25',
    '26',
    '27',
    '28',
    '31',
    '32',
    '33',
    '34',
    '35',
    '36',
    '37',
    '38',
    '41',
    '42',
    '43',
    '44',
    '45',
    '46',
    '47',
    '48']
    
rest_button_data = [
    
    [(0.19757173824074667,0.767496734601214),
    (0.1897053531161016,0.7630481695950905),
    (0.18256140247732544,0.7601311351574772),
    (0.17516643862322845,0.7584561230172182),
    (0.166547109294908,0.7577335612749664),
    (0.15146253533909754,0.8036518636951792),
    (0.14023118921598868,0.8419107316834797),
    (0.1333108280420129,0.8759625672804496),
    (0.13115912144483843,0.9092596452702875),
    (0.13236648228489345,0.9377502496770233),
    (0.13611629044589618,0.9630963488616662),
    (0.14847218531787115,0.9852842627630516),
    (0.17549784605846258,1.0043001840636323),
    (0.20889622012910922,0.9937332594228261),
    (0.2319194767421144,0.9814745884274063),
    (0.2499412711792798,0.9658427961179676),
    (0.26833529053650274,0.9451568256760622),
    (0.2837721260672993,0.9688559091246898),
    (0.29736065807838785,0.9861340808882292),
    (0.31480120898654035,0.998871044998875),
    (0.3417941012085284,1.0089465691170136),
    (0.38882017044210904,0.9665578497336269),
    (0.41053507236815984,0.8990533015905011),
    (0.41117444025007405,0.8241421774483364),
    (0.3949739073512449,0.7595338573242156),
    (0.3885586585751968,0.7600370926904951),
    (0.38217760995205996,0.7610880395288866),
    (0.3761223694833085,0.7628247710148646),
    (0.3706844179140337,0.7653854239520945),
    (0.3621518456247728,0.8047294707457936),
    (0.35532991726299007,0.8339068778511792),
    (0.3483609759648324,0.8572815847797294),
    (0.33938733305235125,0.8792176582993049),
    (0.32057196781126146,0.8807729858114223),
    (0.308556674648187,0.8772607732708657),
    (0.2934151375539694,0.8724445009462785),
    (0.26522091326306746,0.8700874582217294),
    (0.2550291086250304,0.8749720672239478),
    (0.24225738761479798,0.8834455607374354),
    (0.22688515060538406,0.8888138076229627),
    (0.20889184569094615,0.8843823586003426),
    (0.20555841246135223,0.8598269669510082),
    (0.19972851123266638,0.8056580605720022)],
        
    [(0.6293147549194772,0.8017247566603445),
    (0.610882749531951,0.8255303537014809),
    (0.5993398320622966,0.8498916157386621),
    (0.5923041447912945,0.8766409710578262),
    (0.5873938299997251,0.9076108479449112),
    (0.5888294092555094,0.927500193429702),
    (0.5932729476345074,0.9423367606022383),
    (0.6058629942510656,0.9606334924547145),
    (0.6317381618477219,0.9909033319793253),
    (0.6621185235409037,0.9832928912548395),
    (0.6859810041852079,0.9760016731669227),
    (0.7041756764185778,0.9664262666336818),
    (0.7175528673917226,0.9519631969450323),
    (0.7294685824351578,0.9689576506028389),
    (0.7452364754461354,0.9799163340184817),
    (0.765523242614803,0.9876094277636777),
    (0.7909953892467337,0.9948069851537613),
    (0.8176404579600903,0.9547034722667619),
    (0.8227023987319155,0.9062560764922847),
    (0.8124515789462967,0.8589943920657171),
    (0.7931583659873211,0.8224480768506386),
    (0.7737611845634953,0.798558172455814),
    (0.7548049465065069,0.7791577459942235),
    (0.7357425129979669,0.7660588011023457),
    (0.7160267452194867,0.7610734686730417),
    (0.6865588117918818,0.7634037239289848),
    (0.6468492210382288,0.7841386880783165)],

    [(0.7110129073604073,0.3853949694533778),
    (0.7031464904216665,0.3809463726331585),
    (0.6960025715969861,0.3780293381955452),
    (0.6886075759287934,0.37635432605528624),
    (0.679988246600473,0.3756317643130344),
    (0.6915391812222517,0.4173065117600168),
    (0.695157207445211,0.4397708901533083),
    (0.6966170926701342,0.45567259325093223),
    (0.7016935406696129,0.47765921936862504),
    (0.7048234750358608,0.4925852159642623),
    (0.7071638471742465,0.5066360704145199),
    (0.7116631874771574,0.5186113096310685),
    (0.7212699627087895,0.5273104923396748),
    (0.7342417784741246,0.5306246303202076),
    (0.7471978780761686,0.5272058875929099),
    (0.7633273700992294,0.5183630642420762),
    (0.7858194267558072,0.5054049285379055),
    (0.8118681084305827,0.5049715569258523),
    (0.831569178096835,0.5131593598596718),
    (0.8472128052498856,0.5187912183424296),
    (0.8610892230132479,0.510690013377191),
    (0.8782463103284334,0.4791337390775846),
    (0.8852533012850858,0.4501307686590944),
    (0.8920096607955661,0.4180929562064974),
    (0.9084150446568099,0.37743209217637935),
    (0.9019997958807617,0.37793532754265885),
    (0.8956187790717206,0.37898627438105037),
    (0.8895635386029692,0.38072300586702823),
    (0.8841255552195987,0.38328362699016255),
    (0.8755930147444335,0.4226276737838616),
    (0.868771054568555,0.4518050808892472),
    (0.8618021132703974,0.4751798196318931),
    (0.8528285021720119,0.49711586133737296),
    (0.8340131369309222,0.4986711888494903),
    (0.8219978437678477,0.49515900812302943),
    (0.8068563066736301,0.4903427357984422),
    (0.7786620823827282,0.48798569307389317),
    (0.7684702459305953,0.4928702702620158),
    (0.7556985408274107,0.5013437955895992),
    (0.740326287910949,0.5067120106610307),
    (0.722332998903559,0.5022805934525063),
    (0.7189995815810128,0.47772516998907627),
    (0.7131696485382314,0.42355626361007015)],
    
    [(0.10353347071932434,0.3853299096276071),
    (0.09566708559467925,0.3808813446214835),
    (0.08852312700237919,0.37796431018387017),
    (0.08112817905533005,0.37628926622951553),
    (0.07250883381996173,0.37556670448726365),
    (0.07882974584864227,0.4104764389897268),
    (0.07666902790885184,0.43816889136275294),
    (0.07077287382580535,0.4639532615301918),
    (0.0658874615176698,0.4931387812299889),
    (0.06724219320267666,0.5185124632356309),
    (0.06990146188315013,0.5376027340779358),
    (0.0776299488098474,0.5550379402180055),
    (0.09419234318704957,0.575446491745133),
    (0.12534330590703768,0.5643343371316818),
    (0.1439528339487452,0.5517956384656342),
    (0.15888722946565553,0.5381828959276939),
    (0.1790128423323957,0.5238484824421823),
    (0.198465523446225,0.5409527583584537),
    (0.2093940311920665,0.5552172444615476),
    (0.22196401902126606,0.5671510299113582),
    (0.2463410608499301,0.577263394752354),
    (0.2784017794514537,0.5367757584734935),
    (0.2873175843378952,0.4878840152239356),
    (0.289393804039423,0.4337078870451984),
    (0.3009356398298226,0.37736703235060864),
    (0.29452035923967873,0.37787026771688814),
    (0.2881393424306376,0.37892121455527966),
    (0.28208407014779047,0.3806579460412575),
    (0.27664615039261137,0.3832185671643918),
    (0.2681135781033505,0.42256261395809086),
    (0.2612916497415677,0.4517400210634765),
    (0.2543227084434101,0.47511475980612233),
    (0.2453490655309289,0.4970508015116022),
    (0.22653370028983913,0.49860612902371954),
    (0.21451840712676465,0.49509394829725867),
    (0.19937685412549921,0.4902776759726714),
    (0.1711826457416451,0.48792063324812246),
    (0.16099084110360806,0.49280521043624503),
    (0.14821912009337562,0.5012787357638284),
    (0.13284688308396173,0.50664695083526),
    (0.11485357816952382,0.5022155336267357),
    (0.11152014493992989,0.47766011016330556),
    (0.10569024371124407,0.4234912037842994)],
    
    [(0.5343337084851502,0.05438524222997977),
    (0.5389608141965184,0.06428275057545337),
    (0.5414183894635787,0.0744662517345045),
    (0.5424051354567843,0.08479235162414776),
    (0.5426198169747798,0.09511764025434988),
    (0.546891113839488,0.0960979438931698),
    (0.5499538568355511,0.0967762124606396),
    (0.552608934008912,0.09735930120720494),
    (0.5556571697773217,0.09805404947626363),
    (0.554348846904463,0.1017717651681973),
    (0.5507205129144868,0.10672903756506619),
    (0.5462319894041245,0.11200669381299827),
    (0.5423430979701079,0.11668556105812154),
    (0.5423373714328763,0.12119008705863668),
    (0.5423823565642405,0.12510105747509082),
    (0.5424669820588861,0.12991238270779185),
    (0.5425800493551155,0.1371179731570476),
    (0.5460392596121836,0.13807947466529025),
    (0.5489067276886473,0.13873855137951008),
    (0.551895152957082,0.1393378971289942),
    (0.5557172347900625,0.14012023755712538),
    (0.5549141197574188,0.14337047692638166),
    (0.5518972526874003,0.1468131438536694),
    (0.5476610785843796,0.15051282095332336),
    (0.5432001697091122,0.15453413856082193),
    (0.5424592830477191,0.15933092475177368),
    (0.5423395984195775,0.16483364981995766),
    (0.5425546617067218,0.1713602638381136),
    (0.542818082419378,0.17922874869307695),
    (0.5465114444210293,0.18008257539431663),
    (0.5498105661483769,0.1808569463914671),
    (0.5529683696624855,0.18162894723848558),
    (0.5562379042808029,0.18247563167523356),
    (0.5544920103352544,0.1854320360563145),
    (0.5505854302640112,0.1887055633436462),
    (0.5461158679547048,0.1923781189266891),
    (0.5426811545513499,0.19653162410195169),
    (0.5423006579664023,0.20287374817896114),
    (0.5420495174946984,0.20846031929644526),
    (0.5419242972138997,0.21412792091575727),
    (0.5419214339452838,0.22071318421939407),
    (0.5457495604564534,0.22162513527353503),
    (0.5488683598891952,0.2224347244746602),
    (0.5519833416304495,0.22336320295153364),
    (0.5557998241825813,0.22463180592587162),
    (0.5548553909366986,0.22671330676729082),
    (0.552283793950537,0.22922192775095213),
    (0.5486786206222531,0.23231376473756168),
    (0.5446335219781954,0.23614491358782572),
    (0.5424268962982645,0.2428033334045969),
    (0.5416526684645449,0.24788305825593598),
    (0.5416935813916555,0.25269231557241445),
    (0.5419323779942155,0.2585393486916517),
    (0.5450383245322818,0.26140466931665357),
    (0.5486806567243799,0.2629327321487291),
    (0.5524671703983328,0.26364918558460054),
    (0.5560056613819636,0.2640796621139423),
    (0.5556748584145483,0.2691912487821564),
    (0.5524933215850241,0.2726339793376356),
    (0.5479228449640576,0.2753766725306408),
    (0.5434250317377419,0.2783882266466721),
    (0.542930131664544,0.29779953352900274),
    (0.5445626401729058,0.3150199308946938),
    (0.548867087325366,0.3302072802867646),
    (0.5563880031844637,0.3435194432482344),
    (0.5564895537780383,0.34796877179265556),
    (0.5562498663807979,0.3519767752010905),
    (0.5558421369299041,0.3558267898101233),
    (0.5554394977343273,0.35980227921272073),
    (0.5358927900605638,0.3599603316403144),
    (0.516688083915913,0.35999755413232015),
    (0.49828684275895907,0.3599544778466998),
    (0.4811505300482861,0.3598718248259896),
    (0.4608867326567366,0.3599573093012199),
    (0.4428339831044245,0.3601143754918459),
    (0.4251780189540747,0.36013276403917865),
    (0.4061045777684117,0.35980227921272073),
    (0.4057019703869306,0.3558267898101233),
    (0.40529420912194114,0.3519767752010905),
    (0.4050544899106049,0.34796877179265556),
    (0.40515607231827533,0.3435194432482344),
    (0.4126769563632772,0.3302072802867646),
    (0.41698140351573754,0.3150199308946938),
    (0.418613943838195,0.29779953352900274),
    (0.4181190755790929,0.2783882266466721),
    (0.4136212623527771,0.2753766725306408),
    (0.40905072210361926,0.27263394752353987),
    (0.40586918527409493,0.2691912487821564),
    (0.4055383823066797,0.2640796621139423),
    (0.4090769051044062,0.26364918558460054),
    (0.4128634187783591,0.2629327321487291),
    (0.41650575097045717,0.26140466931665357),
    (0.4196116975085236,0.2585393486916517),
    (0.41985052592517935,0.25269231557241445),
    (0.4198914070381942,0.24788305825593598),
    (0.4191171473903788,0.2428033334045969),
    (0.4169105853386394,0.23614491358782572),
    (0.41286545488048587,0.23231376473756168),
    (0.40926028155220207,0.22922192775095213),
    (0.40668868456604046,0.22671330676729082),
    (0.4057442513201577,0.22463180592587162),
    (0.40956070205819384,0.22336320295153364),
    (0.41267568379944797,0.2224347244746602),
    (0.4157945468603814,0.22162513527353503),
    (0.4196226415574552,0.22071318421939407),
    (0.4196197782888394,0.21412792091575727),
    (0.41949455800804053,0.20846031929644526),
    (0.4192434493504325,0.20287374817896114),
    (0.41886292095138905,0.19653162410195169),
    (0.41542820754803417,0.1923781189266891),
    (0.4109586770528236,0.1887055633436462),
    (0.40705206516748466,0.1854320360563145),
    (0.40530617122193613,0.18247563167523356),
    (0.40857573765434924,0.18162894723848558),
    (0.4117335411684579,0.1808569463914671),
    (0.41503259926761404,0.18008257539431663),
    (0.41872599308336106,0.17922874869307695),
    (0.4189894137960172,0.1713602638381136),
    (0.4192044770831615,0.16483364981995766),
    (0.41908479245501995,0.15933092475177368),
    (0.4183439057936268,0.15453413856082193),
    (0.4138829969183594,0.15051282095332336),
    (0.40964685462943445,0.1468131438536694),
    (0.40662995574532024,0.14337047692638166),
    (0.4058268725267722,0.14012023755712538),
    (0.40964892254565705,0.13933788122194632),
    (0.4126373159999959,0.13873853547246223),
    (0.4155047840764597,0.13807947466529025),
    (0.4189640579617192,0.1371179731570476),
    (0.41907712525794866,0.1299123906613158),
    (0.4191617189384985,0.12510106542861477),
    (0.4192067040698627,0.12119008705863668),
    (0.4192009775326311,0.11668555310459762),
    (0.4153120542845188,0.11200668585947433),
    (0.41082356258825226,0.10672902961154225),
    (0.407195228598276,0.10177175721467337),
    (0.40588690572541736,0.0980540415227397),
    (0.40893514149382704,0.097359293253681),
    (0.41159021866718787,0.0967762124606396),
    (0.4146529616632511,0.0960979438931698),
    (0.4189242585279592,0.09511763230082594),
    (0.41913890823185906,0.08479234367062383),
    (0.4201256542250646,0.07446624378098056),
    (0.42258322949212485,0.06428273466840549),
    (0.42721036701758885,0.05438524222997977),
    (0.43927907604739636,0.04223308482706875),
    (0.45089952446834825,0.03475723363457464),
    (0.46490717537660253,0.030037230763670642),
    (0.4841374282401256,0.02615266604667357),
    (0.5017415990426247,0.03064130090637086),
    (0.5231252207898244,0.04243445214600074)]]

rest_button_names = ['CONTOUR',
                'PONTIC',
                'COPING',
                'ANATOMIC COPING',
                'IMPLANT']

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
    name = bpy.props.StringProperty(name="Tooth Number",default="")
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
        
        if not self.properties.name: #eg, it was invoked
            self.properties.name = str(self.teeth[int(self.properties.ob_list)])
        #my_item.abutment = self.properties.abutment
        my_item.name = self.properties.name
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

 
class ButtonMultiSelect(bpy.types.Operator):
    '''Select Multiple Interestingly Shaped Buttons'''
    bl_idname = "view3d.button_multi_select"
    bl_label = "Button Multi Select"

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            #check to see what button the mouse is over if any
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            for i in range(0,len(tooth_button_data)):
                self.tooth_button_hover[i] = point_inside_loop(tooth_button_data[i],self.mouse,self.menu_width, self.menu_loc)

        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            
            
            #determine if we are clicking on a toth
            for i in range(0,len(tooth_button_data)):
                #check every tooth
                self.tooth_button_hover[i] = point_inside_loop(tooth_button_data[i],self.mouse,self.menu_width, self.menu_loc)
                #if we have clicked on it, add it to the current restoration type list
                if self.tooth_button_hover[i]:             
                    self.rest_lists[self.rest_index].append(tooth_button_names[i])

            #no buttons are hovered, this is equiv to enter...
            if True not in self.tooth_button_hover:
                for i in range(0,len(rest_button_data)):
                    self.rest_button_select[i] = point_inside_loop(rest_button_data[i],self.mouse,.5*self.menu_width, self.rest_menu_loc)
                    
                    if self.rest_button_select[i]:
                        self.rest_index = i 
                
                if True not in self.rest_button_select:
                    context.region.callback_remove(self._handle)
                    self.ret_selected = [tooth_button_names[i] for i in range(0,len(tooth_button_data)) if self.tooth_button_select[i]]
                    self.execute(context)
                    return {'FINISHED'}
            

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.mouse = (event.mouse_region_x, event.mouse_region_y)
            for i in range(0,len(tooth_button_data)):
                self.tooth_button_hover[i] = point_inside_loop(tooth_button_data[i],self.mouse,self.menu_width, self.menu_loc)
                if self.tooth_button_hover[i]:
                    self.tooth_button_select[i] = False

            #no buttons are hovered, this is equiv to quiting...
            if True not in self.tooth_button_hover:
                context.region.callback_remove(self._handle)
                return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)

            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._handle = context.region.callback_add(draw_callback_tooth_select, (self, context), 'POST_PIXEL')

            self.mouse = (0,0)
            
            #keep track of which teeth are selected and which one the mouse is over
            self.tooth_button_select = [False]*len(tooth_button_data)
            self.tooth_button_hover = [False]*len(tooth_button_data)
            
            
            #keep track of which rest type is selected
            self.rest_button_select = [False]*5 #keep in mind we only want a subset of them!
            self.rest_button_select[0] = True #make something default
            self.rest_button_hover = [False]*5 #don't think I need this....
            self.rest_index = 0
            
            #form lists for each rest_type
            self.rest_lists = [[],[],[],[],[]] #contour, pontic, coping, anatomic coping, implant

            
            region = bpy.context.region
            rv3d = bpy.context.space_data.region_3d
    
            width = region.width
            height = region.height
            mid = (width/2,height/2)
    
            #need to check height available..whatev
            #menu_width is also our scale!
            self.menu_aspect = 0.5824333739982135
            self.menu_width = .8*width
            self.menu_height = self.menu_width/self.menu_aspect
            if self.menu_height > height:
                self.menu_width = self.menu_aspect*.8*height
                self.menu_height = self.menu_width/self.menu_aspect
            #origin of menu is bottom left corner
            self.menu_loc = (.5*(width - self.menu_width), .5*(height - self.menu_height)) #for now
            
            #middle menu
            self.rest_menu_loc = (self.menu_loc[0] + self.menu_width*.25, self.menu_loc[1] + self.menu_height*.25/self.menu_aspect)

            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}
        
    def execute(self,context):
        for teeth in self.rest_lists:
            print(teeth)      
        #for tooth_name in self.ret_selected:
        #    bpy.ops.view3d.append_working_tooth('EXEC_DEFAULT',name = str(tooth_name))

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
        
        
        #Clear the higher level multires detail
        #unfortunately modifying the base mesh ruins the
        #multires data in most situations...we can be clever
        #and use some shrinkwraps to put it back, but i haven't
        #had time to code it.
        bpy.ops.object.multires_base_apply(modifier = 'Multires')
        mod = Bridge.modifiers['Multires']        
        subdivs = mod.levels #save these.
        mod.levels = 0
        bpy.ops.object.multires_higher_levels_delete(modifier = 'Multires')
        for i in range(0,subdivs):
            bpy.ops.object.multires_subdivide(modifier = 'Multires')
        

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
           InitiateAutoMargin, WalkAroundMargin, CopingFromCrown, DefineAxis, CursorToBound, SliceView, NormalView,ButtonMultiSelect])

    
        
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
    