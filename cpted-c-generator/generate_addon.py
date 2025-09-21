#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# IDS -> Blender Add-on (c-1/c-2) generator — no external deps.
#
# 사용법:
#   python generate_addon.py \
#     --ids input/ids/cpted_c_rules.ids.xml \
#     --out build/ids_auto_addon \
#     --zip
#
# 동작:
#   1) IDS XML 파싱 → ids_cache.json 생성(메서드 소문자, key=Object.Pset.Property)
#   2) 템플릿 렌더링(templates/addon/*.j2) → 없거나 비어 있으면 안전한 기본 코드로 대체
#   3) config/mapping/* → build/ids_auto_addon/data/ 복사(객체 할당 기능용)
#   4) build/zip/ids_auto_addon.zip 패키징(옵션)
#
# 주의:
#   - 외부 라이브러리 미사용
#   - Blender 4.x 매니페스트 포함

import os
import sys
import json
import zipfile
import argparse
from xml.etree import ElementTree as ET
from datetime import datetime

# 기본 애드온 메타 정보
ADDON_ID = "ids_auto_addon"
ADDON_NAME = "IDS Auto Add-on"
VERSION = "0.1.0"
BLENDER_VERSION_MIN = "4.0.0"


def ensure_dir(path: str) -> str:
    """Ensure directory exists."""
    os.makedirs(path, exist_ok=True)
    return path


def read_text(path: str) -> str:
    """Read text from file if exists, else return empty string."""
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_text(path: str, content: str) -> None:
    """Write text to a file, creating directories as needed."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def render_template(src: str, context: dict) -> str:
    """Very simple template renderer: replaces {{KEY}} with context[KEY]."""
    out = src
    for k, v in context.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def parse_ids_to_cache(ids_path: str) -> dict:
    """
    Parse IDS XML to a cache dict.
    Each Property yields a record with method, meta, and key = Object.Pset.Property.
    Only c-type methods are processed here, but others are passed through as-is.
    """
    tree = ET.parse(ids_path)
    root = tree.getroot()
    requirements = []
    for req in root.findall(".//Requirement"):
        obj = (req.findtext("./Object") or "").strip()
        pset = (req.findtext("./Pset") or "").strip()
        for prop in req.findall("./Property"):
            name = (prop.attrib.get("name") or "").strip()
            method = (prop.attrib.get("method") or "a").lower().strip()
            unit = (prop.attrib.get("unit") or "").strip()
            tol_attr = prop.attrib.get("tolerance")
            tol = float(tol_attr) if tol_attr not in (None, "") else None

            # Build key; fallback to property name only if missing object/pset
            key = f"{obj}.{pset}.{name}" if obj and pset and name else name

            # Build meta
            meta = {}
            if unit:
                meta["unit"] = unit
                
            if tol is not None:
                meta["tolerance"] = tol

            # Parse c-specific attributes
            c_node = prop.find("./c")
            if c_node is not None:
                cmeta = {}
                # relation, metric, tie_breaker attributes
                for attr in ("relation", "metric", "tie_breaker"):
                    val = c_node.attrib.get(attr)
                    if val:
                        cmeta[attr] = val
                # target
                tgt = c_node.find("./target")
                if tgt is not None:
                    tmeta = {}
                    for attr in ("ifc", "filter", "role", "psetFilter"):
                        val = tgt.attrib.get(attr)
                        if val:
                            tmeta[attr] = val
                    cmeta["target"] = tmeta
                # scope
                scope = c_node.find("./scope")
                if scope is not None:
                    smeta = {}
                    # include all attributes
                    for k_attr, v_attr in scope.attrib.items():
                        smeta[k_attr] = v_attr
                    if scope.attrib.get("filter"):
                        smeta["filter"] = scope.attrib.get("filter")
                    cmeta["scope"] = smeta
                # threshold
                thr = c_node.find("./threshold")
                if thr is not None:
                    thmeta = {}
                    op = thr.attrib.get("op")
                    val = thr.attrib.get("value")
                    if op:
                        thmeta["op"] = op
                    if val is not None:
                        try:
                            thmeta["value"] = float(val)
                        except:
                            thmeta["value"] = val
                    cmeta["threshold"] = thmeta
                meta["c"] = cmeta
            # Evaluate block
            eval_node = prop.find("./Evaluate")
            if eval_node is not None:
                emeta = {}
                op = eval_node.attrib.get("op")
                thr = eval_node.attrib.get("threshold")
                if op:
                    emeta["op"] = op
                if thr is not None:
                    try:
                        emeta["threshold"] = float(thr)
                    except:
                        emeta["threshold"] = thr
                meta["evaluate"] = emeta

            rec = {
                "requirement_id": req.attrib.get("id"),
                "object": obj,
                "pset": pset,
                "property": name,
                "method": method,
                "key": key,
                "meta": meta,
            }
            requirements.append(rec)
    return {
        "version": 1,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "requirements": requirements,
    }


# -------------------- Fallback Templates --------------------
FALLBACK: dict[str, str] = {}

FALLBACK["__init__.py"] = r'''
bl_info = {
    "name": "{{ADDON_NAME}}",
    "author": "Generated",
    "version": (0, 1, 0),
    "blender": (3, 5, 0),
    "location": "3D Viewport > Sidebar > IDS",
    "description": "Populate IFC Psets/Properties from IDS rules (c-1/c-2)",
    "category": "Import-Export",
}

import bpy
from . import ui as _ui
from . import ops as _ops
from . import assign as _assign

classes = (
    _ui.IDS_PT_rules,
    _ops.IDS_OT_refresh_cache,
    _ops.IDS_OT_rule_search,
    _ops.IDS_OT_rule_add_pset,
    _ops.IDS_OT_rule_execute,
    _assign.IDS_OT_assign_open,
    _assign.IDS_OT_assign_set,
    _assign.IDS_OT_assign_clear,
    _assign.IDS_OT_assign_save,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
'''

FALLBACK["blender_manifest.toml"] = r'''
schema_version = "1.0.0"
id = "{{ADDON_ID}}"
version = "{{VERSION}}"
name = "{{ADDON_NAME}}"
tagline = "Populate IFC Psets/Properties from IDS rules (c-1/c-2)"
maintainers = ["Generated"]
type = "add-on"
blender_version_min = "{{BLENDER_VERSION_MIN}}"
license = "GPL-3.0-or-later"
website = "https://example.local"
'''

FALLBACK["parser.py"] = r'''
import os, json
_CACHE = None

def _cache_path():
    return os.path.join(os.path.dirname(__file__), "ids_cache.json")

def load_cache():
    global _CACHE
    _CACHE = None  # force reload each time
    p = _cache_path()
    if not os.path.exists(p):
        return {"version": 1, "requirements": []}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def list_requirements():
    c = load_cache()
    return c.get("requirements", [])

def get_prop_config_by_key(key: str):
    for r in list_requirements():
        if r.get("key") == key:
            return r
    return None
'''

FALLBACK["methods.py"] = r'''
# Minimal method stubs (c-only pipeline mainly driven by ops)
def get_method_fn(tag: str):
    tag = (tag or "c").lower().strip()
    return method_c

def method_c(obj, key):
    # actual calculation is handled in ops (distance_to / within-count)
    return None
'''

FALLBACK["ops.py"] = r'''
import bpy, json
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty
from mathutils import Vector
from . import parser

LAST_SEARCH = {}
DATA_DIR = "data"

def _scene_mesh_objects():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]

def _bbox_center(obj):
    cs = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return sum(cs, Vector()) / 8.0

def _min_center_distance(src, targets):
    if not targets:
        return None
    sc = _bbox_center(src)
    dists = [(t, (sc - _bbox_center(t)).length) for t in targets]
    tmin, dmin = min(dists, key=lambda x: x[1])
    return float(dmin)

def _count_targets_inside(src, targets):
    if not targets:
        return 0
    corners = [src.matrix_world @ Vector(c) for c in src.bound_box]
    mins = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
    maxs = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
    def _inside(p): return (mins.x <= p.x <= maxs.x) and (mins.y <= p.y <= maxs.y) and (mins.z <= p.z <= maxs.z)
    cnt = 0
    for t in targets:
        if _inside(_bbox_center(t)):
            cnt += 1
    return int(cnt)

def _ensure_pset_prop(obj, pset, prop, value=None):
    key = f"{pset}.{prop}"
    if key not in obj.keys():
        obj[key] = value if value is not None else ""
    return True

def _auto_find(rule, role="sources"):
    want_ifc = rule.get("object") if role == "sources" else ((rule.get("meta") or {}).get("c", {}).get("target", {})).get("ifc", "")
    name_filter = ((rule.get("meta") or {}).get("c", {}).get("target", {})).get("filter", "") if role == "targets" else ""
    out = []
    for o in _scene_mesh_objects():
        cond_ifc = (not want_ifc) or (want_ifc in o.name) or (str(o.get("ifc_class","")) == want_ifc)
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
    apply_to: EnumProperty(items=[("search","search",""),("active","active","")], default="search")
    def execute(self, context):
        r = parser.get_prop_config_by_key(self.rule_key)
        if not r:
            self.report({'WARNING'}, "Rule not found")
            return {'CANCELLED'}
        pset, prop = r.get("pset",""), r.get("property","")
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
    apply_to: EnumProperty(items=[("search","search",""),("active","active","")], default="search")
    def execute(self, context):
        r = parser.get_prop_config_by_key(self.rule_key)
        if not r:
            self.report({'WARNING'}, "Rule not found")
            return {'CANCELLED'}
        cmeta = (r.get("meta") or {}).get("c", {})
        relation = (cmeta.get("relation") or "distance_to").lower()
        pset, prop = r.get("pset",""), r.get("property","")
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
'''

FALLBACK["assign.py"] = r'''
import bpy, os, json
from bpy.types import Operator
from bpy.props import StringProperty
from . import parser

ASSIGN_PATH = None
ASSIGN = {}

def _data_dir():
    return os.path.join(os.path.dirname(__file__), "data")

def _assign_path():
    global ASSIGN_PATH
    if ASSIGN_PATH is None:
        ASSIGN_PATH = os.path.join(_data_dir(), "assignment_user.json")
    return ASSIGN_PATH

def _load():
    global ASSIGN
    p = _assign_path()
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            ASSIGN = json.load(f)
    else:
        ASSIGN = {}

def _save():
    os.makedirs(_data_dir(), exist_ok=True)
    with open(_assign_path(), "w", encoding="utf-8") as f:
        json.dump(ASSIGN, f, ensure_ascii=False, indent=2)

class IDS_OT_assign_open(Operator):
    bl_idname = "ids.assign_open"
    bl_label = "Open Assignment"
    def execute(self, context):
        _load()
        self.report({'INFO'}, f"Assignment loaded: {len(ASSIGN)} rules")
        return {'FINISHED'}

class IDS_OT_assign_set(Operator):
    bl_idname = "ids.assign_set"
    bl_label = "Assign from Selection"
    rule_key: StringProperty()
    role: StringProperty()  # "sources" or "targets"
    def execute(self, context):
        _load()
        sel = [o.name for o in context.selected_objects]
        if not sel:
            self.report({'WARNING'}, "No selection")
            return {'CANCELLED'}
        if self.rule_key not in ASSIGN:
            ASSIGN[self.rule_key] = {"sources": [], "targets": []}
        ASSIGN[self.rule_key][self.role] = sel
        _save()
        self.report({'INFO'}, f"Assigned {self.role}: {len(sel)} items")
        return {'FINISHED'}

class IDS_OT_assign_clear(Operator):
    bl_idname = "ids.assign_clear"
    bl_label = "Clear Assignment"
    rule_key: StringProperty()
    def execute(self, context):
        _load()
        if self.rule_key in ASSIGN:
            ASSIGN.pop(self.rule_key, None)
            _save()
            self.report({'INFO'}, "Assignment cleared")
        else:
            self.report({'INFO'}, "Nothing to clear")
        return {'FINISHED'}

class IDS_OT_assign_save(Operator):
    bl_idname = "ids.assign_save"
    bl_label = "Save Assignment"
    def execute(self, context):
        _save()
        self.report({'INFO'}, "Assignment saved")
        return {'FINISHED'}
'''

FALLBACK["ui.py"] = r'''
import bpy
from bpy.types import Panel
from . import parser

class IDS_PT_rules(Panel):
    bl_label = "IDS (C-Types)"
    bl_idname = "IDS_PT_rules"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "IDS"

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("ids.refresh_cache", icon="FILE_REFRESH")
        row.operator("ids.assign_open", text="객체 할당 열기", icon="OUTLINER").bl_idname = "ids.assign_open"

        reqs = [r for r in parser.list_requirements() if (r.get("method") or "").lower() == "c"]
        if not reqs:
            layout.label(text="No c-type rules.")
            return

        for r in reqs:
            key = r.get("key", "")
            cmeta = (r.get("meta") or {}).get("c", {})
            relation = cmeta.get("relation", "?")
            box = layout.box()
            box.label(text=key)
            box.label(text=f"relation={relation}")
            
            row = box.row(align=True)
            op = row.operator("ids.rule_search", text="대상 검색", icon="VIEWZOOM")
            op.rule_key = key
            
            row = box.row(align=True)
            op = row.operator("ids.rule_add_pset", text="Pset/Property 추가", icon="ADD")
            op.rule_key = key; op.apply_to = "search"
            op = row.operator("ids.rule_add_pset", text="(활성객체)", icon="DOT")
            op.rule_key = key; op.apply_to = "active"
            
            row = box.row(align=True)
            op = row.operator("ids.rule_execute", text="값 계산·기입", icon="CHECKMARK")
            op.rule_key = key; op.apply_to = "search"
            op = row.operator("ids.rule_execute", text="(활성객체)", icon="CHECKMARK")
            op.rule_key = key; op.apply_to = "active"
            
            # 객체 할당 기능
            row = box.row(align=True)
            op = row.operator("ids.assign_set", text="소스=선택지정", icon="EXPORT")
            op.rule_key = key; op.role = "sources"
            op = row.operator("ids.assign_set", text="타겟=선택지정", icon="IMPORT")
            op.rule_key = key; op.role = "targets"
            op = row.operator("ids.assign_clear", text="할당 해제", icon="X")
            op.rule_key = key
            row = box.row(align=True)
            row.operator("ids.assign_save", text="할당 저장", icon="FILE_TICK")
'''


def load_template_or_fallback(base_dir: str, name: str, ctx: dict) -> str:
    """Load template from templates/addon/name.j2 or fallback if missing/empty."""
    tpath = os.path.join(base_dir, "templates", "addon", name + ".j2")
    src = read_text(tpath).strip()
    if not src:
        src = FALLBACK[name if name in FALLBACK else name]
    return render_template(src, ctx)


def copy_mapping_files(base_dir: str, out_dir: str) -> None:
    """Copy mapping files into data/ directory with sensible defaults."""
    data_dir = os.path.join(out_dir, "data")
    ensure_dir(data_dir)
    # object_alias.csv
    path_alias = os.path.join(base_dir, "config", "mapping", "object_alias.csv")
    if os.path.exists(path_alias) and os.path.getsize(path_alias) > 0:
        with open(path_alias, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "alias,ifc\nCCTV,IfcAudioVisualAppliance\nEntranceLight,IfcLightFixture\n"
    write_text(os.path.join(data_dir, "object_alias.csv"), content)
    # assignment_user.json (seed)
    path_seed = os.path.join(base_dir, "config", "mapping", "assignment_seed.json")
    if os.path.exists(path_seed) and os.path.getsize(path_seed) > 0:
        with open(path_seed, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "{}"
    write_text(os.path.join(data_dir, "assignment_user.json"), content)


def build_addon(base_dir: str, ids_path: str, out_dir: str, make_zip: bool = True) -> str:
    """Main generator logic: produce ids_cache.json, render templates, copy mapping, optionally zip."""
    # 1) Parse IDS to cache
    cache = parse_ids_to_cache(ids_path)
    ensure_dir(out_dir)
    write_text(os.path.join(out_dir, "ids_cache.json"), json.dumps(cache, ensure_ascii=False, indent=2))
    # 2) Render templates to files
    context = {
        "ADDON_ID": ADDON_ID,
        "ADDON_NAME": ADDON_NAME,
        "VERSION": VERSION,
        "BLENDER_VERSION_MIN": BLENDER_VERSION_MIN,
    }
    write_text(os.path.join(out_dir, "__init__.py"), load_template_or_fallback(base_dir, "__init__.py", context))
    write_text(os.path.join(out_dir, "blender_manifest.toml"), load_template_or_fallback(base_dir, "blender_manifest.toml", context))
    write_text(os.path.join(out_dir, "parser.py"), load_template_or_fallback(base_dir, "parser.py", context))
    write_text(os.path.join(out_dir, "methods.py"), load_template_or_fallback(base_dir, "methods.py", context))
    write_text(os.path.join(out_dir, "ops.py"), load_template_or_fallback(base_dir, "ops.py", context))
    write_text(os.path.join(out_dir, "assign.py"), load_template_or_fallback(base_dir, "assign.py", context))
    write_text(os.path.join(out_dir, "ui.py"), load_template_or_fallback(base_dir, "ui.py", context))
    # 3) Copy mapping files
    copy_mapping_files(base_dir, out_dir)
    # 4) Create zip
    zip_dir = os.path.join(base_dir, "build", "zip")
    ensure_dir(zip_dir)
    zip_path = os.path.join(zip_dir, f"{ADDON_ID}.zip")
    if make_zip:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _, files in os.walk(out_dir):
                for fn in files:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, os.path.join(out_dir, ".."))
                    z.write(full, arcname=rel)
    return zip_path


def main() -> None:
    parser_arg = argparse.ArgumentParser(description="IDS→Blender Add-on generator (c-1/c-2)")
    parser_arg.add_argument("--ids", default="input/ids/cpted_c_rules.ids.xml", help="IDS XML path")
    parser_arg.add_argument("--out", default="build/ids_auto_addon", help="Addon output folder")
    parser_arg.add_argument("--no-zip", action="store_true", help="Do not create ZIP")
    args = parser_arg.parse_args()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ids_path = os.path.join(base_dir, args.ids)
    out_dir = os.path.join(base_dir, args.out)
    if not os.path.exists(ids_path):
        print(f"[ERR] IDS not found: {ids_path}")
        sys.exit(2)
    zip_path = build_addon(base_dir, ids_path, out_dir, make_zip=not args.no_zip)
    print("[OK] Add-on built at:", out_dir)
    if not args.no_zip:
        print("[OK] ZIP:", zip_path)


if __name__ == "__main__":
    main()