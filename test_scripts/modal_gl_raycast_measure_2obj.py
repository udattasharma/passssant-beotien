import bpy
import bgl
import blf
from mathutils import Matrix, Vector
from mathutils.geometry import interpolate_bezier as bezlerp
from bpy_extras.view3d_utils import location_3d_to_region_2d
from bpy_extras.view3d_utils import region_2d_to_vector_3d
from bpy_extras.view3d_utils import region_2d_to_location_3d

#http://www.blender.org/documentation/blender_python_api_2_63_12/bpy_extras.view3d_utils.html
#bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)


#borrowed from edge filet from Zeffi (included with blend)
def draw_polyline_from_coordinates(context, points, LINE_TYPE):  
    region = context.region  
    rv3d = context.space_data.region_3d  
  
    bgl.glColor4f(1.0, 1.0, 1.0, 1.0)  
  
    if LINE_TYPE == "GL_LINE_STIPPLE":  
        bgl.glLineStipple(4, 0x5555)  
        bgl.glEnable(bgl.GL_LINE_STIPPLE)  
        bgl.glColor4f(0.3, 0.3, 0.3, 1.0)  
      
    bgl.glBegin(bgl.GL_LINE_STRIP)  
    for coord in points:  
        vector3d = (coord.x, coord.y, coord.z)  
        vector2d = location_3d_to_region_2d(region, rv3d, vector3d)  
        bgl.glVertex2f(*vector2d)  
    bgl.glEnd()  
      
    if LINE_TYPE == "GL_LINE_STIPPLE":  
        bgl.glDisable(bgl.GL_LINE_STIPPLE)  
        bgl.glEnable(bgl.GL_BLEND)  # back to uninterupted lines  
      
    return
  
#borrowed from edge filet from Zeffi (included with blend)  
def draw_polyline_from_coordinates2D(context, points, LINE_TYPE):  
    region = context.region  
    rv3d = context.space_data.region_3d  
  
    bgl.glColor4f(1.0, 1.0, 1.0, 1.0)  
  
    if LINE_TYPE == "GL_LINE_STIPPLE":  
        bgl.glLineStipple(4, 0x5555)  
        bgl.glEnable(bgl.GL_LINE_STIPPLE)  
        bgl.glColor4f(0.3, 0.3, 0.3, 1.0)  
      
    bgl.glBegin(bgl.GL_LINE_STRIP)  
    for coord in points:  
        bgl.glVertex2f(coord[0],coord[1])  
    bgl.glEnd()  
      
    if LINE_TYPE == "GL_LINE_STIPPLE":  
        bgl.glDisable(bgl.GL_LINE_STIPPLE)  
        bgl.glEnable(bgl.GL_BLEND)  # back to uninterupted lines  
      
    return
    
#borrowed from edge filet from Zeffi (included with blend)  
def draw_points(context, points, size):  
    region = context.region  
    rv3d = context.space_data.region_3d  
      
      
    bgl.glEnable(bgl.GL_POINT_SMOOTH)  
    bgl.glPointSize(size)  
    # bgl.glEnable(bgl.GL_BLEND)  
    bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)  
      
    bgl.glBegin(bgl.GL_POINTS)  
    # draw red  
    bgl.glColor4f(1.0, 0.2, 0.2, 1.0)      
    for coord in points:  
        vector3d = (coord.x, coord.y, coord.z)  
        vector2d = location_3d_to_region_2d(region, rv3d, vector3d)  
        bgl.glVertex2f(*vector2d)  
    bgl.glEnd()  
      
    bgl.glDisable(bgl.GL_POINT_SMOOTH)  
    bgl.glDisable(bgl.GL_POINTS)  
    return



#from the template...a few practice items

#put text above the active object
#draw a cross hair on the mouse
#display the distance from raycast onto active oject to cursor.
def draw_callback_px(self, context):  
    
    region = context.region  
    rv3d = context.space_data.region_3d  
    
    #get the firs object information
    ob = bpy.context.object   
    mx = ob.matrix_world
    imx = mx.inverted()
    ob_loc_3d = ob.location + Vector((0,0,1))    
    ob_loc2D = location_3d_to_region_2d(region, rv3d, ob_loc_3d)
    
    #simple attempt to keep the results out of the way
    mouse_quad = [-1,-1]    
    if self.mouse[0] > ob_loc2D[0]:
        mouse_quad[0] = 1
    if self.mouse[1] > ob_loc2D[1]:
        mouse_quad[1] = 1
        
    #get 2nd obj
    ob2 = [obj for obj in bpy.context.selected_objects if obj != ob][0]
    mx2 = ob2.matrix_world
    imx2 = mx2.inverted()
        
    #this is from this thread.
    #http://blenderartists.org/forum/showthread.php?247286-mouse-coordinate-to-view-3d-coordinate&p=2067020&viewfull=1#post2067020
    vec = region_2d_to_vector_3d(region, rv3d, self.mouse)
    loc = region_2d_to_location_3d(region, rv3d, self.mouse, vec)
    
    #raycast what I think is the ray onto the object
    #raycast needs to be in ob coordinates.
    a = loc + 3000*vec
    b = loc - 3000*vec       
    hit = ob.ray_cast(imx*a, imx*b)
    
    
    if hit[2] != -1:
        close_pt = mx2*ob2.closest_point_on_mesh(imx2*(mx*hit[0]))[0]
        close_pt_gl = location_3d_to_region_2d(region, rv3d, close_pt)
        thick =  close_pt- mx*hit[0]
        
        
        #print out the thickness here...
        bgl.glColor4f(1.0, 1.0, 1.0, 1.0)         
        blf.position(0,self.mouse[0]+15,self.mouse[1]+30*mouse_quad[1],0)
        blf.size(0,20,72)
        blf.draw(0,str(thick.length)[0:5])
        
        #draw a point on ob2 showing the closest point        
        bgl.glEnable(bgl.GL_POINT_SMOOTH)  
        bgl.glPointSize(3)  
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)  
      
        bgl.glBegin(bgl.GL_POINTS)  
        # draw red  
        bgl.glColor4f(1.0, 0.2, 0.2, 1.0)       
        bgl.glVertex2f(*close_pt_gl)
        bgl.glEnd()
        bgl.glDisable(bgl.GL_POINT_SMOOTH) 
              
    bgl.glLineWidth(1)  
    bgl.glDisable(bgl.GL_BLEND)  
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0) 
    return


class RaycastThickness2Obj(bpy.types.Operator):
    '''Measure thickness between two surfaces'''
    bl_idname = "view3d.raycast_thickness"
    bl_label = "Measure Thickness"
    bl_options = {'REGISTER','UNDO'}
    
    ob1 = bpy.props.StringProperty(name="Tooth Number",default="Unknown")
    ob2 = bpy.props.StringProperty(name="Insertion Axis",default="")
    
    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':                        
            self.mouse = (event.mouse_region_x, event.mouse_region_y)

        elif event.type == 'LEFTMOUSE':
            context.region.callback_remove(self._handle)
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            context.region.callback_remove(self._handle)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)

            # Add the region OpenGL drawing callback
            # draw in view space with 'POST_VIEW' and 'PRE_VIEW'
            self._handle = context.region.callback_add(draw_callback_px, (self, context), 'POST_PIXEL')
            self.mouse =(0,0)
            return {'RUNNING_MODAL'}
  
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}


def register():
    bpy.utils.register_class(RaycastThickness2Obj)


def unregister():
    bpy.utils.unregister_class(RaycastThickness2Obj)

if __name__ == "__main__":
    register()