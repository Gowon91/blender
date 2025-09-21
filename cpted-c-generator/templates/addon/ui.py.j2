"""
Blender UI panels for IDS add-on (Jinja2 template).

This UI module defines the main panel for interacting with IDS
requirement rules of type 'c'. Each rule appears as its own boxed
subpanel with buttons to search for matching objects, add
Pset/Property definitions, compute and write values, and manually
assign source/target objects. A top row provides quick access to
refresh the cache and open the assignment manager.  The implementation
guards against runtime errors during draw() so that UI issues in
individual rules do not break the entire panel.
"""

import bpy
from bpy.types import Panel
from . import parser


class IDS_PT_rules(Panel):
    """Panel listing c-type IDS rules and actions."""
    bl_label = "IDS (C-Types)"
    bl_idname = "IDS_PT_rules"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "IDS"

    def draw(self, context):
        layout = self.layout
        # Top row: refresh cache and open assignment editor
        top = layout.row(align=True)
        top.operator("ids.refresh_cache", icon="FILE_REFRESH")
        top.operator("ids.assign_open", text="객체 할당 열기", icon="OUTLINER")

        # Load the cached requirements; handle errors gracefully
        try:
            reqs = parser.list_requirements()
        except Exception as e:
            layout.box().label(text=f"load error: {e}")
            return

        # Show count of total requirements and note filtering
        layout.label(text=f"rules: {len(reqs)} (method=c only)")

        if not reqs:
            layout.label(text="No IDS rules loaded.")
            return

        shown = 0
        for i, r in enumerate(reqs):
            try:
                method = (r.get("method") or "").lower().strip()
                if method != "c":
                    continue
                key = r.get("key", f"<no-key-{i}>")
                cmeta = (r.get("meta") or {}).get("c", {})
                relation = cmeta.get("relation", "?")

                box = layout.box()
                box.label(text=key)
                box.label(text=f"relation={relation}")

                # Search button
                row = box.row(align=True)
                op = row.operator("ids.rule_search", text="대상 검색", icon="VIEWZOOM")
                op.rule_key = key

                # Add Pset/Property buttons (search result and active object)
                row = box.row(align=True)
                op = row.operator("ids.rule_add_pset", text="Pset/Property", icon="ADD")
                op.rule_key = key
                op.apply_to = "search"
                op2 = row.operator("ids.rule_add_pset", text="(활성객체)", icon="DOT")
                op2.rule_key = key
                op2.apply_to = "active"

                # Compute & write buttons (search result and active object)
                row = box.row(align=True)
                op = row.operator("ids.rule_execute", text="값 계산·기입", icon="CHECKMARK")
                op.rule_key = key
                op.apply_to = "search"
                op2 = row.operator("ids.rule_execute", text="(활성객체)", icon="CHECKMARK")
                op2.rule_key = key
                op2.apply_to = "active"

                # Manual assignment actions: set sources/targets and clear
                row = box.row(align=True)
                op = row.operator("ids.assign_set", text="소스=선택지정", icon="EXPORT")
                op.rule_key = key
                op.role = "sources"
                op2 = row.operator("ids.assign_set", text="타겟=선택지정", icon="IMPORT")
                op2.rule_key = key
                op2.role = "targets"
                op3 = row.operator("ids.assign_clear", text="할당 해제", icon="X")
                op3.rule_key = key

                shown += 1
            except Exception as e:
                err = layout.box(); err.alert = True
                err.label(text=f"[rule {i}] draw error: {e}")

        if shown == 0:
            layout.label(text="No c-type rules after filter.")