"""
Operators for IDS add-on (Jinja2 template).

This module defines a set of Blender operators used to interact with
IDS-derived rules. Operators handle refreshing the cache, searching
for applicable objects, adding Pset/Property definitions, and computing
distances or inclusion counts according to c-1/c-2 rules. No Jinja
placeholders are required in this file.
"""

import bpy
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty
from mathutils import Vector
from . import parser

# Persistent caches for the current session
LAST_SEARCH: dict[str, list[str]] = {}
DATA_DIR = "data"

def _scene_mesh_objects():
    """Return all mesh-type objects in the current scene."""
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]

def _bbox_center(obj):
    """Compute the center of an object's bounding box in world coordinates."""
    cs = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sum(cs, Vector()) / 8.0

def _min_center_distance(src, targets):
    """
    Compute the minimum distance between the center of src and the centers
    of targets. Returns None if targets is empty.
    """
    if not targets:
        return None
    sc = _bbox_center(src)
    dists = [(t, (sc - _bbox_center(t)).length) for t in targets]
    _, dmin = min(dists, key=lambda x: x[1])
    return float(dmin)

def _count_targets_inside(src, targets):
    """
    Count the number of target objects whose bounding box centers lie inside
    the bounding box of src. Returns 0 if targets is empty.
    """
    if not targets:
        return 0
    corners = [src.matrix_world @ Vector(c) for c in src.bound_box]
    mins = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
    maxs = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
    def _inside(p):
        return (mins.x <= p.x <= maxs.x) and (mins.y <= p.y <= maxs.y) and (mins.z <= p.z <= maxs.z)
    cnt = 0
    for t in targets:
        if _inside(_bbox_center(t)):
            cnt += 1
    return int(cnt)

def _ensure_pset_prop(obj, pset: str, prop: str, value=None):
    """
    Ensure that a custom property (pset.prop) exists on obj. If not,
    optionally initialize it with a value.
    """
    key = f"{pset}.{prop}"
    if key not in obj.keys():
        obj[key] = value if value is not None else ""
    return True

def _auto_find(rule: dict, role: str = "sources"):
    """
    Automatically find candidate objects for a rule.

    Parameters
    ----------
    rule : dict
        The requirement dictionary.
    role : str
        "sources" to find source objects or "targets" to find target objects.

    Returns
    -------
    list of bpy.types.Object
    """
    want_ifc = rule.get("object") if role == "sources" else ((rule.get("meta") or {}).get("c", {}).get("target", {})).get("ifc", "")
    name_filter = ((rule.get("meta") or {}).get("c", {}).get("target", {})).get("filter", "") if role == "targets" else ""
    out = []
    for o in _scene_mesh_objects():
        cond_ifc = (not want_ifc) or (want_ifc in o.name) or (str(o.get("ifc_class", "")) == want_ifc)
        cond_name = (not name_filter) or any(tok in o.name for tok in name_filter.replace('"','').split("|"))
        if cond_ifc and cond_name:
            out.append(o)
    return out

class IDS_OT_refresh_cache(Operator):
    bl_idname = "ids.refresh_cache"
    bl_label = "Refresh IDS Cache"
    def execute(self, context):
        parser.load_cache()
        self.report({'INFO'}, "IDS cache reloaded")
        return {'FINISHED'}

class IDS_OT_rule_search(Operator):
    bl_idname = "ids.rule_search"
    bl_label = "Search Targets/Sources"
    rule_key: StringProperty()
    def execute(self, context):
        r = parser.get_prop_config_by_key(self.rule_key)
        if not r:
            self.report({'WARNING'}, "Rule not found")
            return {'CANCELLED'}
        sources = _auto_find(r, "sources")
        targets = _auto_find(r, "targets")
        LAST_SEARCH[self.rule_key] = [o.name for o in sources]
        self.report({'INFO'}, f"검색 완료: sources={len(sources)}, targets={len(targets)}")
        return {'FINISHED'}

class IDS_OT_rule_add_pset(Operator):
    bl_idname = "ids.rule_add_pset"
    bl_label = "Add Pset/Property"
    rule_key: StringProperty()
    apply_to: EnumProperty(items=[("search", "search", ""), ("active", "active", "")], default="search")
    def execute(self, context):
        r = parser.get_prop_config_by_key(self.rule_key)
        if not r:
            self.report({'WARNING'}, "Rule not found")
            return {'CANCELLED'}
        pset, prop = r.get("pset", ""), r.get("property", "")
        if not pset or not prop:
            self.report({'WARNING'}, "Invalid pset/property")
            return {'CANCELLED'}
        if self.apply_to == "active" and context.active_object:
            objs = [context.active_object]
        else:
            names = LAST_SEARCH.get(self.rule_key, [])
            objs = [bpy.data.objects[n] for n in names if n in bpy.data.objects]
        count = 0
        for o in objs:
            if _ensure_pset_prop(o, pset, prop):
                count += 1
        self.report({'INFO'}, f"Pset/Property 추가: {count}개")
        return {'FINISHED'}

class IDS_OT_rule_execute(Operator):
    bl_idname = "ids.rule_execute"
    bl_label = "Compute & Write"
    rule_key: StringProperty()
    apply_to: EnumProperty(items=[("search", "search", ""), ("active", "active", "")], default="search")
    def execute(self, context):
        r = parser.get_prop_config_by_key(self.rule_key)
        if not r:
            self.report({'WARNING'}, "Rule not found")
            return {'CANCELLED'}
        cmeta = (r.get("meta") or {}).get("c", {})
        relation = (cmeta.get("relation") or "distance_to").lower()
        pset, prop = r.get("pset", ""), r.get("property", "")
        if not pset or not prop:
            self.report({'WARNING'}, "Invalid pset/property")
            return {'CANCELLED'}
        if self.apply_to == "active" and context.active_object:
            sources = [context.active_object]
        else:
            names = LAST_SEARCH.get(self.rule_key, [])
            sources = [bpy.data.objects[n] for n in names if n in bpy.data.objects]
            if not sources:
                sources = _auto_find(r, "sources")
        targets = _auto_find(r, "targets")
        written = 0
        for s in sources:
            if relation == "distance_to":
                val = _min_center_distance(s, [t for t in targets if t])
            elif relation == "within":
                val = _count_targets_inside(s, [t for t in targets if t])
            else:
                val = None
            if val is not None:
                s[f"{pset}.{prop}"] = float(val) if isinstance(val, (int, float)) else val
                written += 1
        self.report({'INFO'}, f"값 계산/기입: {written}개, relation={relation}")
        return {'FINISHED'}