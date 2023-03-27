bl_info = {
    "name": "CG HOOD",
    "author": "Rawbin",
    "version": (1, 0, 0),
    "blender": (3, 4, 1),
    "description": "",
}


import bpy
import os
import functools
from pathlib import Path
import bpy.utils.previews
import concurrent.futures
from functools import partial
import random


preview_collections = {}
loaded_categories = set()


def cached(func):
    @functools.cache
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def check_context_property(func):
    def wrapper(*args, **kwargs):
        if bpy.context.scene is not None and hasattr(bpy.context.scene, "my_property"):
            return func(*args, **kwargs)
        else:
            return None
    return wrapper


@cached
def get_assetfolder():
    home_directory = Path.home()
    cg_hood_folder_path = home_directory / "CG Hood"
    if not cg_hood_folder_path.exists():
        for path in home_directory.rglob("CG Hood"):
            if path.is_dir():
                cg_hood_folder_path = path
                break
        else:
            raise Exception("The CG Hood directory has not been found.")
    test_folder_path = cg_hood_folder_path / "TEST"
    return str(test_folder_path)


@cached
def get_categories():
    return os.listdir(get_assetfolder())


@cached
def get_category_index():
    if hasattr(bpy.context, "scene") and bpy.context.scene is not None and hasattr(bpy.context.scene, "my_property"):
        _, category_index = bpy.context.scene.my_property.category_enum.split(
            " ")
        return int(category_index)
    else:
        return 0


@cached
def get_categoryfolder():
    return os.path.join(get_assetfolder(), get_categories()[get_category_index()])


season_filtered_categories = ["Coni", "Deci"]


def filter_files(file_list, search_str, winter_bool, spring_bool, summer_bool, autumn_bool):
    category_name = get_categories()[get_category_index()]
    if category_name in season_filtered_categories:
        filtered_files = [file for file in file_list
                        if (winter_bool and "winter" in file.lower()) or
                        (spring_bool and "spring" in file.lower()) or
                        (summer_bool and "summer" in file.lower()) or
                        (autumn_bool and "autumn" in file.lower())]
    else:
        filtered_files = file_list

    if search_str:
        filtered_files = [file for file in filtered_files if search_str in file.lower()]

    return filtered_files


def get_iconfolder():
    return os.path.abspath(os.path.join(get_categoryfolder(), "Iconfiles"))


@cached
@check_context_property
def get_iconfiles():
    winter_bool = bpy.context.scene.my_property.winter_bool
    spring_bool = bpy.context.scene.my_property.spring_bool
    summer_bool = bpy.context.scene.my_property.summer_bool
    autumn_bool = bpy.context.scene.my_property.autumn_bool
    search_str = bpy.context.scene.my_property.search_str.lower()

    iconfiles = [file for file in os.listdir(get_iconfolder()) if file.endswith(".jpg")]

    iconfiles = filter_files(iconfiles, search_str, winter_bool, spring_bool, summer_bool, autumn_bool)
    return iconfiles


@cached
@check_context_property
def get_iconfileslist():
    return [os.path.join(get_iconfolder(), file) for file in get_iconfiles()]


@cached
@check_context_property
def get_asset_index():
    asset_enum_split = bpy.context.scene.my_property.asset_enum.split(" ")
    if len(asset_enum_split) == 2:
        _, asset_index = asset_enum_split
        return int(asset_index)
    else:
        return None

@cached
@check_context_property
def get_blendfileslist():
    index_to_use = 0 if get_asset_index() is None else get_asset_index()
    return get_iconfileslist()[index_to_use].replace("Iconfiles", "Blendfiles").replace(".jpg", ".blend")


@cached
@check_context_property
def get_object():
    object_list = get_iconfiles()
    if not object_list:
        return None

    index_to_use = 0 if get_asset_index() is None else get_asset_index()
    object = object_list[index_to_use].replace(".jpg", "")
    return object


def update_selected_asset(context):
    scene = context.scene
    my_property = scene.my_property
    filtered_assets = get_iconfiles()
    items = [(f'asset {i}', asset, "")
             for i, asset in enumerate(filtered_assets)]

    if hasattr(bpy.types.Scene.my_property, "asset_enum"):
        bpy.types.Scene.my_property.asset_enum.items = items

    if not filtered_assets:
        if items:
            my_property.asset_enum = 'asset 0'
    else:
        current_enum_value = my_property.asset_enum
        if current_enum_value not in [f'asset {i}' for i, _ in enumerate(filtered_assets)]:
            if items:
                my_property.asset_enum = f'asset 0'


def category_callback(self, context):
    return [(f'category {i}', category, "") for i, category in enumerate(get_categories())]


def load_category_icons(category_index, category):
    category_folder = os.path.join(get_assetfolder(), category)
    icon_files_folder = os.path.abspath(
        os.path.join(category_folder, "Iconfiles"))
    icon_files = [file for file in os.listdir(
        icon_files_folder) if file.endswith(".jpg")]
    icon_files_list = [os.path.join(icon_files_folder, file)
                       for file in icon_files]

    pcoll = bpy.utils.previews.new()
    preview_collections[f"category_{category_index}_thumbnails"] = pcoll

    for i, icon_file in enumerate(icon_files_list):
        pcoll.load(os.path.basename(icon_file), icon_file, 'IMAGE')


def load_all_icons():
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for category_index, category in enumerate(get_categories()):
            executor.submit(partial(load_category_icons, category_index, category))


def load_icons_on_startup():
    if not preview_collections:
        load_all_icons()
        

def asset_callback(self, context):
    filtered_assets = get_iconfiles()
    category_index = get_category_index()
    pcoll = preview_collections.get(f"category_{category_index}_thumbnails")
    if pcoll:
        icon_files_list = get_iconfileslist()
        valid_indices = [i for i, _ in enumerate(
            filtered_assets) if i < len(icon_files_list)]
        return [(f'asset {i}', asset, "", pcoll[os.path.basename(icon_files_list[i])].icon_id, i) for i, asset in zip(valid_indices, filtered_assets)]
    else:
        return []


def clear_caches():
    get_category_index.cache_clear()
    get_categoryfolder.cache_clear()
    get_iconfileslist.cache_clear()
    get_iconfiles.cache_clear()
    get_blendfileslist.cache_clear()
    get_asset_index.cache_clear()
    get_object.cache_clear()
    loaded_categories.clear()


def update_enum(self, context):
    clear_caches()
    update_selected_asset(context)
    update_filters(self, context)


def update_filters(self, context):
    clear_caches()
    update_selected_asset(context)
    filtered_assets = get_iconfiles()
    items = [(f'asset {i}', asset, "")
             for i, asset in enumerate(filtered_assets)]

    if hasattr(bpy.types.Scene.my_property, "asset_enum"):
        bpy.types.Scene.my_property.asset_enum.items = items

    object_name = get_object()
    if object_name is None:
        warning_filters(self, "No asset found. Please check your filters.")
    else:
        warning_filters(self, "")
        

def set_bool_prop(self, prop_name, value):
    self[prop_name] = value
    update_filters(self, bpy.context)


def set_season_bool(self, season, value):
    prop_name = f"{season}_bool"
    set_bool_prop(self, prop_name, value)


def warning_filters(self, message):
    self.warning_message_filter = message
    
    
def update_seed_value(self, context):
    obj = context.active_object
    if obj and "CGH0" in obj.name:
        tree = obj.modifiers.get('Tree')
        if tree:
            node_test = tree.node_group
            for node in node_test.nodes:
                if node.name.startswith('Secondary Trunk') or node.name == 'Main Tree':
                    node.inputs[1].default_value = self.seed_value


def secondary_trunk_nodes_items(self, context):
    items = []
    obj = context.active_object
    if obj and "CGH0" in obj.name:
        tree = obj.modifiers.get('Tree')
        if tree:
            node_test = tree.node_group
            secondary_trunk_nodes = [node for node in node_test.nodes if node.name.startswith('Secondary Trunk')]
            for i, node in enumerate(secondary_trunk_nodes):
                items.append((str(i), node.name, ""))
    if not items:
        items.append(('0', "No secondary trunk", ""))
    return items


class AssetSystemProperty(bpy.types.PropertyGroup):
    category_enum: bpy.props.EnumProperty(
        name="Category",
        items=category_callback,
        update=update_enum,
    )

    asset_enum: bpy.props.EnumProperty(
        name="Assets",
        items=asset_callback,
        update=update_enum,
    )

    winter_bool: bpy.props.BoolProperty(
        name='Winter',
        default=True,
        update=update_filters,
        get=lambda self: self.get("winter_bool", True),
        set=lambda self, value: set_season_bool(self, "winter", value),
    )

    spring_bool: bpy.props.BoolProperty(
        name='Spring',
        default=True,
        update=update_filters,
        get=lambda self: self.get("spring_bool", True),
        set=lambda self, value: set_season_bool(self, "spring", value),
    )

    summer_bool: bpy.props.BoolProperty(
        name='Summer',
        default=True,
        update=update_filters,
        get=lambda self: self.get("summer_bool", True),
        set=lambda self, value: set_season_bool(self, "summer", value),
    )

    autumn_bool: bpy.props.BoolProperty(
        name='Autumn',
        default=True,
        update=update_filters,
        get=lambda self: self.get("autumn_bool", True),
        set=lambda self, value: set_season_bool(self, "autumn", value),
    )

    search_str: bpy.props.StringProperty(
        name='Search',
        update=update_filters,
    )
    
    filters: bpy.props.BoolProperty(
        name="Filter assets",
        default=False,
    )
    
    general_settings: bpy.props.BoolProperty(
        name="General settings",
        default=False,
    )
    
    warning_message_filter: bpy.props.StringProperty()
    
    seed_value: bpy.props.IntProperty(
        name="Value", 
        update=update_seed_value,
    )

    secondary_trunk_nodes: bpy.props.EnumProperty(
        name="",
        items=secondary_trunk_nodes_items,
    )
    
    main_trunk_settings: bpy.props.BoolProperty(
        name="Main trunk settings",
        default=False,
    )
    
    secondary_trunk_settings: bpy.props.BoolProperty(
        name="Secondary trunk settings",
        default=False,
    )

    weather_settings: bpy.props.BoolProperty(
        name="Weather settings",
        default=False,
    )


class CGH_OT_seed_control(bpy.types.Operator):
    bl_idname = "cgh.seed_control"
    bl_label = "Seed Control"

    action: bpy.props.EnumProperty(
        items=[
            ('RANDOMIZE', "Randomize", "Randomize the seed value"),
            ('RESET', "Reset", "Reset the seed value to its default"),
        ],
        name="Action",
    )

    def execute(self, context):
        obj = context.active_object
        scene = context.scene
        myproperty = scene.my_property
        if obj and "CGH0" in obj.name:
            tree = obj.modifiers.get('Tree')
            if tree:
                node_test = tree.node_group
                for node in node_test.nodes:
                    if node.name.startswith('Secondary Trunk') or node.name == 'Main Tree':
                        if self.action == 'RANDOMIZE':
                            random_seed = random.randint(0, 1000000)
                            node.inputs[1].default_value = random_seed
                            myproperty.seed_value = random_seed
                        elif self.action == 'RESET':
                            default_seed = 0
                            node.inputs[1].default_value = default_seed
                            myproperty.seed_value = default_seed
        return {'FINISHED'}
    

class CGH_OT_add_SECONDARY_TRUNK(bpy.types.Operator):
    bl_idname = "cgh.add_secondary_trunk"
    bl_label = "Add secondary trunk"

    def execute(self, context):
        obj = context.active_object
        if obj and "CGH0" in obj.name:
            tree = obj.modifiers.get('Tree')
            if tree:
                node_test = tree.node_group
                
                file_path = r"C:\Users\Anwender\OneDrive\Bureau\CG Hood\TEST\Coni\Blendfiles\ST Spring.blend"
                inner_path = 'NodeTree'
                object_name = "GN_SECONDARY_TRUNK"

                bpy.ops.wm.append(
                    filepath=os.path.join(file_path, inner_path, object_name),
                    directory=os.path.join(file_path, inner_path),
                    filename=object_name,
                    link=False
                )

                st_node = node_test.nodes.new(type="GeometryNodeGroup")
                st_node.node_tree = bpy.data.node_groups[object_name]
                st_node.location = (0, 0)
                st_node.name = "Secondary Trunk"
                
                st_nodes = [node for node in node_test.nodes if node.name.startswith("Secondary Trunk")]
                st_node.location = (150 * len(st_nodes), 0)

                main_tree_node = None
                join_geometry_wood_node = None
                join_geometry_leaves_needles_node = None

                for node in node_test.nodes:
                    if node.name == "Main Tree":
                        main_tree_node = node
                    if node.name == "Join Geometry Wood":
                        join_geometry_wood_node = node
                    if node.name == "Join Geometry Leaves/Needles":
                        join_geometry_leaves_needles_node = node

                if main_tree_node and join_geometry_wood_node and join_geometry_leaves_needles_node:
                    node_test.links.new(main_tree_node.outputs['Secondary Trunk Output'], st_node.inputs['Geometry'])
                    node_test.links.new(main_tree_node.outputs['Secondary Trunk Parent Radius Geometry Output'], st_node.inputs['Parent Radius'])
                    node_test.links.new(st_node.outputs['Wood Material Geometry'], join_geometry_wood_node.inputs[0])
                    node_test.links.new(st_node.outputs['Leaves/Needles Geometry'], join_geometry_leaves_needles_node.inputs[0])
                    
                join_geometry_wood_node.location.x = st_node.location.x + 300
                join_geometry_leaves_needles_node.location.x = join_geometry_wood_node.location.x + 150

                wood_material_node = node_test.nodes.get("Wood Material")
                leaves_node = node_test.nodes.get("Leaves")
                needles_node = node_test.nodes.get("Needles")
                join_geometry_node = node_test.nodes.get("Join Geometry")
                group_output_node = next(node for node in node_test.nodes if node.type == 'GROUP_OUTPUT')

                if wood_material_node:
                    wood_material_node.location.x = join_geometry_leaves_needles_node.location.x + 150
                if leaves_node:
                    leaves_node.location.x = join_geometry_leaves_needles_node.location.x + 300
                if needles_node:
                    needles_node.location.x = join_geometry_leaves_needles_node.location.x + 450
                if join_geometry_node:
                    join_geometry_node.location.x = join_geometry_leaves_needles_node.location.x + 600
                if group_output_node:
                    group_output_node.location.x = join_geometry_leaves_needles_node.location.x + 750

                node_test.nodes.update()

        return {'FINISHED'}



class CGH_OT_remove_SECONDARY_TRUNK(bpy.types.Operator):
    bl_idname = "cgh.remove_secondary_trunk"
    bl_label = "Remove secondary trunk"

    def execute(self, context):
        obj = context.active_object
        scene = context.scene
        if obj and "CGH0" in obj.name:
            tree = obj.modifiers.get('Tree')
            if tree:
                node_test = tree.node_group
                selected_node_index = int(scene.my_property.secondary_trunk_nodes)
                selected_node = None

                secondary_trunk_nodes = [node for node in node_test.nodes if node.name.startswith('Secondary Trunk')]
                
                if not secondary_trunk_nodes:
                    return {'CANCELLED'}
                
                if 0 <= selected_node_index < len(secondary_trunk_nodes):
                    selected_node = secondary_trunk_nodes[selected_node_index]

                if selected_node:
                    new_selected_index = selected_node_index - 1 if selected_node_index > 0 else selected_node_index + 1

                    node_test.nodes.remove(selected_node)
                    node_test.nodes.update()

                    secondary_trunk_nodes = [node for node in node_test.nodes if node.name.startswith('Secondary Trunk')]
                    if secondary_trunk_nodes:
                        scene.my_property.secondary_trunk_nodes = str(new_selected_index % len(secondary_trunk_nodes))
                    else:
                        scene.my_property.secondary_trunk_nodes = '0'


        return {'FINISHED'}


class AssetSystemPanel(bpy.types.Panel):
    bl_label = "Asset System"
    bl_idname = "VIEW3D_PT_assetsystem"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CG Hood"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        scene = context.scene
        myproperty = scene.my_property
        row.scale_y = 2.5
        row.operator("wm.selectasset")

        obj = context.active_object
        
        if obj and "CGH0" in obj.name:
            tree = None
            if obj:
                tree = obj.modifiers.get('Tree')
            if tree:
                node_test = tree.node_group
                wood_material_node = None
                seed_control_node = None

                for n in node_test.nodes:
                    if n.name == 'Wood Material':
                        wood_material_node = n
                    if n.name.startswith('Secondary Trunk') or n.name == 'Main Tree':
                        seed_control_node = n
                    if wood_material_node and seed_control_node:
                        break
                    
                if wood_material_node: 
                    row = layout.row(align=True)
                    row.prop(myproperty, "general_settings", icon='DOWNARROW_HLT' if myproperty.general_settings else 'RIGHTARROW', emboss=False, icon_only=True)
                    row.label(text="General tree settings:")
                    if myproperty.general_settings:
                        column = layout.column()
                        material_box = column.box()
                        material_box.label(text="Material control:")
                        material_box.prop(wood_material_node.inputs[2], 'default_value', text="Material")
                        material_box.prop(wood_material_node.inputs[1], 'default_value', text="UV visualisation")
                        
                        column.separator()
                            
                        if seed_control_node:
                            seed_box = column.box()
                            seed_box.label(text="Seed control:")
                            seed_box.prop(myproperty, 'seed_value', text="Value")
                            row = seed_box.row(align=True)
                            row.operator("cgh.seed_control", text="Randomize", icon="ANIM").action = 'RANDOMIZE'
                            row.separator()
                            row.operator("cgh.seed_control", text="Reset", icon="FILE_REFRESH").action = 'RESET'
                        
            layout.separator()
            
            tree = None
            if obj:
                tree = obj.modifiers.get('Tree')
            if tree:
                row = layout.row(align=True)
                row.prop(myproperty, "main_trunk_settings", icon='DOWNARROW_HLT' if myproperty.main_trunk_settings else 'RIGHTARROW', emboss=False, icon_only=True)
                row.label(text="Main trunk settings:")
                if myproperty.main_trunk_settings:
                    node_test = tree.node_group
                    node = node_test.nodes['Main Tree']
                        
                    column = layout.column()
                    column.prop(node.inputs[4], 'default_value', text="Lenght")
                
            layout.separator()
            
            row = layout.row(align=True)
            row.prop(myproperty, "secondary_trunk_settings", icon='DOWNARROW_HLT' if myproperty.secondary_trunk_settings else 'RIGHTARROW', emboss=False, icon_only=True)
            row.label(text="Secondary trunk settings:")
            if myproperty.secondary_trunk_settings:
                box = layout.box()
                box.scale_y = 1.5
                box.operator("cgh.add_secondary_trunk", icon="ADD")
                box.operator("cgh.remove_secondary_trunk", icon="REMOVE")
        
                if myproperty.secondary_trunk_nodes == "":
                    selected_node_index = -1
                else:
                    selected_node_index = int(myproperty.secondary_trunk_nodes)

                secondary_trunk_nodes_list = secondary_trunk_nodes_items(self, context)
                
                if len(secondary_trunk_nodes_list) == 1 and secondary_trunk_nodes_list[0][1] == "No secondary trunk":
                    row = layout.row()
                else:
                    layout.prop(myproperty, "secondary_trunk_nodes")
                    selected_node = None

                    filtered_nodes = [node for node in node_test.nodes if node.name.startswith('Secondary Trunk')]

                    for i, node in enumerate(filtered_nodes):
                        if i == selected_node_index:
                            selected_node = node
                            break
                        
                    if selected_node:
                        column = layout.column()
                        column.prop(selected_node.inputs[3], 'default_value', text="Position")
                                    
            layout.separator()
                            
            snow = None
            if obj and obj.material_slots:
                if len(obj.material_slots) > 0 and obj.material_slots[0].material:
                    snow = obj.material_slots[0].material.node_tree.nodes['Snow'].node_tree.nodes['Value.002']
            if snow:
                row = layout.row(align=True)
                row.prop(myproperty, "weather_settings", icon='DOWNARROW_HLT' if myproperty.weather_settings else 'RIGHTARROW', emboss=False, icon_only=True)
                row.label(text="Weather settings:")
                if myproperty.weather_settings:
                    row = layout.row()
                    row.prop(snow.outputs[0], 'default_value', text="Snow")
                
        else:
            row = layout.row()
            row.alignment = 'CENTER'
            row.label(text="No CG HOOD asset selected", icon='INFO')


class WM_OT_SelectAssetOP(bpy.types.Operator):
    bl_label = "Select asset"
    bl_idname = "wm.selectasset"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        object_name = get_object()
        if object_name is None:
            return {"CANCELLED"}
        
        file_path = get_blendfileslist()
        inner_path = 'Collection'

        bpy.ops.wm.append(
            filepath=os.path.join(file_path, inner_path, object_name),
            directory=os.path.join(file_path, inner_path),
            filename=object_name,
            link=False
        )

        return {"FINISHED"}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        object_name = get_object()
        layout = self.layout
        scene = context.scene
        myproperty = scene.my_property
        layout.separator()
        layout.prop(myproperty, "category_enum")
        layout.separator()
        row = layout.row(align=True)
        row.prop(myproperty, "filters", icon='DOWNARROW_HLT' if myproperty.filters else 'RIGHTARROW', emboss=False, icon_only=True)
        row.label(text="Filter assets")
        if myproperty.filters:
            box = layout.box()
            category_name = get_categories()[get_category_index()]
            if category_name in season_filtered_categories:
                row = box.row()
                row.prop(myproperty, "winter_bool")
                row.prop(myproperty, "spring_bool")
                row.prop(myproperty, "summer_bool")
                row.prop(myproperty, "autumn_bool")
                layout.separator()
            row = box.row()
            row.prop(myproperty, "search_str", icon="VIEWZOOM")
        if myproperty.warning_message_filter:
            layout.label(text=myproperty.warning_message_filter, icon='ERROR') 
        layout.separator()
        if object_name is not None:
            layout.template_icon_view(
                myproperty, "asset_enum", show_labels=True, scale=15.0, scale_popup=7.5)
        layout.separator()
        layout.label(text=f"Asset : {object_name}")
        layout.separator()


classes = (
    AssetSystemPanel,
    WM_OT_SelectAssetOP,
    AssetSystemProperty,
    CGH_OT_seed_control,
    CGH_OT_add_SECONDARY_TRUNK,
    CGH_OT_remove_SECONDARY_TRUNK,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    load_all_icons()
    bpy.types.Scene.my_property = bpy.props.PointerProperty(
        type=AssetSystemProperty)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.my_property

    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()


if __name__ == "__main__":
    register()
