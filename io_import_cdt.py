bl_info = {
    'name': "CDT Total Importer",
    'author': "patmo141, batFINGER, NotYourBuddy",
    'version': (0,0,1),
    'blender': (2, 6, 3),
    'api': 47879,
    'location': "File > Import-Export > CDT",
    'description': "Tool to import models from .cdt files",
    'warning': "",
    'wiki_url': "",
    'tracker_url': "",
    'category': "Import-Export"}
    
import bpy
import math
import struct
import os
from ctypes import cdll, c_char_p, c_int, create_string_buffer

#identify the addon folder
add_folder = os.path.sys.path[2]
if 'addons' not in add_folder:
    add_folder = os.path.sys.path[1]
    
#by the dll's which handle the importing   
tri_dll = 'io_import_cdt_tri.dll'
model_dll = "io_import_cdt.dll"
bottom_dll = "io_import_cdt_bottom.dll"

#############################################
#### Use ctypes to load .dll libraries ######
#############################################

#for the model
file_path = os.path.join(add_folder,model_dll)
lib = cdll.LoadLibrary(file_path)
lib.Load.argtypes = [c_int, c_char_p]

#for the restoration top
file_path = os.path.join(add_folder,tri_dll)
tlib = cdll.LoadLibrary(file_path)
tlib.Load.argtypes = [c_int, c_char_p]

#for the restoration intaglio
file_path = os.path.join(add_folder,bottom_dll)
blib = cdll.LoadLibrary(file_path)
blib.Load.argtypes = [c_int, c_char_p]



##########################################
####    Classes For Different Records  ###
##########################################

class CDT_Reader(object):
    def __init__(self):
        self.obj = lib.CDT_New()

    def Load(self, filepath):
        fp = create_string_buffer(filepath.encode('utf-8'))
        if(lib.Load(self.obj, fp) == 1):
            return True
        return False
    
    def Unload(self):
     	lib.Unload(self.obj)

    def Decrypt(self):
        if(lib.Decrypt(self.obj) == 1):
            return True
        return False

    def Decompress(self):
        if(lib.Decompress(self.obj) == 1):
            return True
        return False

    def DumpModel(self):
        if(lib.DumpModel(self.obj) == 1):
            return True
        return False
    
class CDT_Tri_Reader(object):
    def __init__(self):
        self.obj = tlib.CDT_New()

    def Load(self, filepath):
        fp = create_string_buffer(filepath.encode('utf-8'))
        if(tlib.Load(self.obj, fp) == 1):
            return True
        return False
    
    def Unload(self):
     	tlib.Unload(self.obj)

    def Decrypt(self):
        if(tlib.Decrypt(self.obj) == 1):
            return True
        return False

    def Decompress(self):
        if(tlib.Decompress(self.obj) == 1):
            return True
        return False

    def DumpModel(self):
        if(tlib.DumpModel(self.obj) == 1):
            return True
        return False

class CDT_Bottom_Reader(object):
    def __init__(self):
        self.obj = blib.CDT_New()

    def Load(self, filepath):
        fp = create_string_buffer(filepath.encode('utf-8'))
        if(blib.Load(self.obj, fp) == 1):
            return True
        return False
    
    def Unload(self):
     	blib.Unload(self.obj)

    def Decrypt(self):
        if(blib.Decrypt(self.obj) == 1):
            return True
        return False

    def Decompress(self):
        if(blib.Decompress(self.obj) == 1):
            return True
        return False

    def DumpModel(self):
        if(blib.DumpModel(self.obj) == 1):
            return True
        return False
    
    
#####################################################
#####   Functions for Each Record Type  #############
#####################################################

def import_cdt_file(context, filepath, scale):
    print(filepath)

    path, ext = os.path.splitext(filepath)
    modelFilepath = path + ".model"
    cdt = CDT_Reader()
    if(cdt.Load(filepath) == False):
        print("Failed to load: " + filepath)
        return {"CANCELLED"}
    if(cdt.Decrypt() == False):
        print("Failed to decrypt: " + filepath)
        return {"CANCELLED"}
    if(cdt.Decompress() == False):
        print("Failed to decompress: " + filepath)
        return {"CANCELLED"}
    if(cdt.DumpModel() == False):
        print("Failed to dump .model file: " + modelFilepath)
        return {"CANCELLED"}
    cdt.Unload()

    MODEL = open(modelFilepath,'rb')
    model = MODEL.read()
    MODEL.close()
    #remove the .model file, or not since it seems to crash in the multiple model scenario?
    #os.remove(modelFilepath)    
 
    
    #Scale factor, ~39.37...mystery. Look for 1/39.37 toward end of record.
    s = scale
    
    #Header is 45 Bytes but I will set a variable in case it changes
    hlen = 45   
    
    #Next 4 bytes is the number of vertices in the primary model
    nverts = struct.unpack('<I', model[hlen:hlen+4])[0]
    
    #Next 4 bytes is the number of faces in the primary model
    nfaces = struct.unpack('<I', model[hlen+4:hlen+8])[0]
       
    #Vertex data starts 8 bytes after the header
    vstart = hlen + 8
    
    #Face data starts after verts data
    fstart = hlen + 8 + nverts*12
    
    #we will make a list of 4 member tupples which contain the info for each mesh.
    model_info = []
    model_info.append((nverts,nfaces,vstart,fstart))
        
    print(model_info)
    
    #Total data after the header
    data_len = len(model) - 45 - 8
    
    #some simple criteria to keep looking and to index the meshes we find
    keepon = 1
    i = 0
    print('here we go')
    
    while keepon > 0:
        
        #keepon += -.5
        print('testing')
        #end of current data = start of data + verts*12 + faces*12
        dend = model_info[i][2] + model_info[i][0]*12 + model_info[i][1]*12
         
        data_diff = data_len - dend    
        
        #not very robust way to decide if there is another mesh after
        if data_diff > 1000:
            
            #this is what we are looking for to denote another mesh record starting    
            seeker = struct.pack('<II',0,0)
            
            #look for the "seeker" from the end of the last mesh we found to the end of the file
            found = model.find(seeker,dend,len(model)-1)
            
            #diag printout to tell me where it's finding other meshes
            print('found another mesh @ : ')
            print(found)
            print(found - dend)
           
            #gather information about the mesh    
            n_vs = struct.unpack('<I', model[found+15:found + 19])[0]
            n_fs = struct.unpack('<I', model[found +19:found + 23])[0]
            v_st = found + 23
            f_st = found + 23 + n_vs*12
            
            model_info.append((n_vs, n_fs, v_st, f_st))
            
            i += 1
            
        else:
            keepon = -1
            
    #for mod in model_info:
    for m in range(0,len(model_info)):    
        mod = model_info[m]
        #I could just use mod[n] here but for clarity, I will
        #pull it apart
        nverts = mod[0]
        nfaces = mod[1]
        vstart = mod[2]
        fstart = mod[3]
        
        #empty lists to populate with vertices and faces
        verts = []
        faces = []
    
        #unpack the vert data
        for i in range(0,nverts):
            
            v = [0,0,0]
            start = vstart + i*12
            v[0] = struct.unpack('<f', model[start:start+4])[0]
            v[1] = struct.unpack('<f', model[start+4:start+8])[0]
            v[2] = struct.unpack('<f', model[start+8:start+12])[0]
            
            verts.append((-v[0]/s,v[1]/s,v[2]/s))
    
        #unpack the face data 
        for i in range(0,nfaces):
        
            f = [0,0,0]
            start = fstart + i*12
        
            f[0] = struct.unpack('<I', model[start:start+4])[0]
            f[1] = struct.unpack('<I', model[start+4:start+8])[0]
            f[2] = struct.unpack('<I', model[start+8:start+12])[0]
        
            faces.append(f)
        
        
        # create new mesh structure    
        full_name = os.path.basename(filepath)
        name = full_name.split('.')[0]
        print(name)
        mesh = bpy.data.meshes.new(name) 
        mesh.from_pydata(verts, [], faces)  
        mesh.update()
    
        new_object = bpy.data.objects.new(name, mesh)
        new_object.data = mesh
    
        scene = bpy.context.scene
        scene.objects.link(new_object)
        scene.objects.active = new_object
        new_object.select = True
        
        #The prep model needs it's normals flipped
        if m == 0:
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.flip_normals()
            bpy.ops.object.mode_set(mode = 'OBJECT')
            
    return {'FINISHED'}

def import_cdt_tri(context, filepath, scale):
    print(filepath)

    path, ext = os.path.splitext(filepath)
    modelFilepath = path + ".tri"
    cdt = CDT_Tri_Reader()
    if(cdt.Load(filepath) == False):
        print("Failed to load: " + filepath)
        return {"CANCELLED"}
    if(cdt.Decrypt() == False):
        print("Failed to decrypt: " + filepath)
        return {"CANCELLED"}
    if(cdt.Decompress() == False):
        print("Failed to decompress: " + filepath)
        return {"CANCELLED"}
    if(cdt.DumpModel() == False):
        print("Failed to dump .tri file: " + modelFilepath)
        return {"CANCELLED"}
    cdt.Unload()

    MODEL = open(modelFilepath,'rb')
    model = MODEL.read()
    MODEL.close()
    #remove the .tri file, or not since it seems to crash in the multiple model scenario?
    #os.remove(modelFilepath)    
    
    s = scale

    print('the record is this long:  ')
    l = len(model)
    print(l)
    
    #looks like n verts is at 36
    nverts = struct.unpack('<I',model[36:40])[0]
    print(nverts)
    #looks like nfaces is at 40
    nfaces = struct.unpack('<I',model[40:44])[0]
    print(nfaces)
    
    #print(model[42:100])
    
    verts = []
    faces = []
    
    
    fdata = [0,0,0]
    for i in range(0,nverts):
        start = 44 + i*12
        vdata = [0,0,0]
        vdata[0] = -struct.unpack('<f',model[start:start+4])[0]/s
        vdata[1] = struct.unpack('<f',model[start+4:start+8])[0]/s
        vdata[2] = struct.unpack('<f',model[start+8:start+12])[0]/s
        verts.append(vdata)
        
    fstart = 44 + nverts*12
    
  
    for i in range(0,nfaces):
        start = fstart + i*12
        fdata = [0,0,0]
        fdata[0] = struct.unpack('<I',model[start:start+4])[0]
        fdata[1] = struct.unpack('<I',model[start+4:start+8])[0]
        fdata[2] = struct.unpack('<I',model[start+8:start+12])[0]
        faces.append(fdata)
    print("whats left")
    print(l - nverts*12 - nfaces*12 - 44)
    

    # create new mesh structure    
    full_name = os.path.basename(filepath)
    name = full_name.split('.')[0]
    print(name)
    mesh = bpy.data.meshes.new(name) 
    mesh.from_pydata(verts, [], faces)  
    mesh.update()
    
    new_object = bpy.data.objects.new(name, mesh)
    new_object.data = mesh
    
    scene = bpy.context.scene
    scene.objects.link(new_object)
    scene.objects.active = new_object
         
    return {'FINISHED'}

def import_cdt_bottom(context, filepath, scale):
    print(filepath)

    path, ext = os.path.splitext(filepath)
    modelFilepath = path + ".bottom"
    cdt = CDT_Bottom_Reader()
    if(cdt.Load(filepath) == False):
        print("Failed to load: " + filepath)
        return {"CANCELLED"}
    if(cdt.Decrypt() == False):
        print("Failed to decrypt: " + filepath)
        return {"CANCELLED"}
    if(cdt.Decompress() == False):
        print("Failed to decompress: " + filepath)
        return {"CANCELLED"}
    if(cdt.DumpModel() == False):
        print("Failed to dump .bottom file: " + modelFilepath)
        return {"CANCELLED"}
    cdt.Unload()

    MODEL = open(modelFilepath,'rb')
    model = MODEL.read()
    MODEL.close()
    #remove the .bottom file, or not since it seems to crash in the multiple model scenario?
    #os.remove(modelFilepath)    
    
    s = scale

    print('the record is this long:  ')
    l = len(model)
    print(l)
        
    
    #looks like n verts is at 36
    nverts = struct.unpack('<I',model[36:40])[0]
    print(nverts)
    #looks like nfaces is at 40
    nfaces = struct.unpack('<I',model[40:44])[0]
    print(nfaces)
    
    #print(model[42:100])
    
    verts = []
    faces = []
    
    
    fdata = [0,0,0]
    for i in range(0,nverts):
        start = 44 + i*12
        vdata = [0,0,0]
        vdata[0] = -struct.unpack('<f',model[start:start+4])[0]/s
        vdata[1] = struct.unpack('<f',model[start+4:start+8])[0]/s
        vdata[2] = struct.unpack('<f',model[start+8:start+12])[0]/s
        verts.append(vdata)
        
    fstart = 44 + nverts*12
    
  
    for i in range(0,nfaces):
        start = fstart + i*12
        fdata = [0,0,0]
        fdata[0] = struct.unpack('<I',model[start:start+4])[0]
        fdata[1] = struct.unpack('<I',model[start+4:start+8])[0]
        fdata[2] = struct.unpack('<I',model[start+8:start+12])[0]
        faces.append(fdata)
    print("whats left")
    print(l - nverts*12 - nfaces*12 - 44)
    

    # create new mesh structure    
    full_name = os.path.basename(filepath)
    name = full_name.split('.')[0]
    print(name)
    mesh = bpy.data.meshes.new(name) 
    mesh.from_pydata(verts, [], faces)  
    mesh.update()
    
    new_object = bpy.data.objects.new(name, mesh)
    new_object.data = mesh
    
    scene = bpy.context.scene
    scene.objects.link(new_object)
    scene.objects.active = new_object
         
    return {'FINISHED'}


#####################################################
#####             Operators             #############
#####################################################

# ExportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, CollectionProperty,FloatProperty


class ImportCDT(bpy.types.Operator, ImportHelper):
    '''This appears in the tooltip of the operator and in the generated docs.'''
    bl_idname = "import_mesh.cdt"  # this is important since its how bpy.ops.export.some_data is constructed
    bl_label = "Import CDT"

    # ExportHelper mixin class uses this
    filename_ext = ".cdt"

    filter_glob = StringProperty(
            default="*.cdt",
            options={'HIDDEN'},
            )
    files = CollectionProperty(
        name="Files",
        type=bpy.types.OperatorFileListElement,
        )
    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    restoration = BoolProperty(
            name="Restoration",
            description="Only use if CDT is complete",
            default=False,
            )
            
    intaglio = BoolProperty(
            name="Intaglio",
            description="Only use if CDT is complete",
            default=False,
            )
            
    scale = FloatProperty("scale",min=0.1,max=100,default=39.37)
    type = EnumProperty(
            name="Example Enum",
            description="Choose between two items",
            items=(('OPT_A', "First Option", "Description one"),
                   ('OPT_B', "Second Option", "Description two")),
            default='OPT_A',
            )

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        import_cdt_file(context, self.filepath, self.scale)
        
        if self.restoration:
            import_cdt_tri(context, self.filepath, self.scale)
        if self.intaglio:
            import_cdt_bottom(context, self.filepath, self.scale)
            
        return {'FINISHED'}
                
                

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.prop(self,"restoration")
        box.prop(self,"intaglio")
        box.prop(self,"type")
        box.prop(self,"scale",text="Scale")
        box.operator('file.select_all_toggle')
        if len(self.files):
            for file in self.files:
                box.label(file.name)
        
# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ImportCDT.bl_idname, text="Import CDT")


def register():
    bpy.utils.register_class(ImportCDT)
    bpy.types.INFO_MT_file_import.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ImportCDT)
    bpy.types.INFO_MT_file_import.remove(menu_func_export)


if __name__ == "__main__":
    register()