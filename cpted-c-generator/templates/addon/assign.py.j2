"""
Object assignment utilities and operators (Jinja2 template).

This module implements the "객체 할당 기능" allowing users to manually
associate a specific Blender object with a given IDS rule.  Assignments
persist across sessions by writing to a JSON file within the add-on's
data directory.  The generator does not inject any variables into
this template; paths are computed relative to this module at runtime.
"""

import os
import json
import bpy
from bpy.types import Operator
from bpy.props import StringProperty

from . import parser


# -----------------------------------------------------------------------------
# File handling helpers
#
# Assignments are stored in a JSON file in the add-on's `data` directory.  The
# structure of the file is a dictionary mapping rule keys to a list of
# assigned object names.  Even though most rules will map to a single object,
# a list is used to allow for future extensions (e.g. multiple targets).
#

def _data_dir() -> str:
    """Return the absolute path to the bundled data directory."""
    return os.path.join(os.path.dirname(__file__), "data")


def _assign_path() -> str:
    """Return the full path of the assignment JSON file."""
    return os.path.join(_data_dir(), "assignment_user.json")


def load_assignments() -> dict:
    """Load the current assignment mapping from disk. If missing, return {}."""
    path = _assign_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def save_assignments(data: dict) -> None:
    """Save the assignment mapping to disk."""
    path = _assign_path()
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_assignment(rule_key: str) -> list[str]:
    """Return the list of assigned object names for a given rule key."""
    data = load_assignments()
    return data.get(rule_key, [])


def assign_object(rule_key: str, object_name: str) -> None:
    """Assign a Blender object to a rule key and persist the change."""
    if not rule_key or not object_name:
        return
    data = load_assignments()
    data[rule_key] = [object_name]
    save_assignments(data)


def clear_assignment(rule_key: str) -> None:
    """Remove any assignment for the given rule key and persist the change."""
    data = load_assignments()
    if rule_key in data:
        data.pop(rule_key)
        save_assignments(data)


# -----------------------------------------------------------------------------
# Blender operators

class IDS_OT_assign_open(Operator):
    bl_idname = "ids.assign_open"
    bl_label = "Show Assignments"
    bl_description = "Display current rule-object assignments in the Info bar"

    def execute(self, context):
        assignments = load_assignments()
        if not assignments:
            self.report({'INFO'}, "No assignments defined")
        else:
            for key, objs in assignments.items():
                self.report({'INFO'}, f"{key}: {', '.join(objs)}")
        return {'FINISHED'}


class IDS_OT_assign_set(Operator):
    bl_idname = "ids.assign_set"
    bl_label = "Assign Selected Object"
    bl_description = "Assign the active object to the selected IDS rule"

    rule_key: StringProperty()

    def execute(self, context):
        r = parser.get_prop_config_by_key(self.rule_key)
        if not r:
            self.report({'WARNING'}, "Rule not found")
            return {'CANCELLED'}
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object to assign")
            return {'CANCELLED'}
        assign_object(self.rule_key, obj.name)
        self.report({'INFO'}, f"Assigned {obj.name} to {self.rule_key}")
        return {'FINISHED'}


class IDS_OT_assign_clear(Operator):
    bl_idname = "ids.assign_clear"
    bl_label = "Clear Assignment"
    bl_description = "Clear any manual object assignment for the selected IDS rule"

    rule_key: StringProperty()

    def execute(self, context):
        r = parser.get_prop_config_by_key(self.rule_key)
        if not r:
            self.report({'WARNING'}, "Rule not found")
            return {'CANCELLED'}
        clear_assignment(self.rule_key)
        self.report({'INFO'}, f"Cleared assignment for {self.rule_key}")
        return {'FINISHED'}


class IDS_OT_assign_save(Operator):
    bl_idname = "ids.assign_save"
    bl_label = "Save Assignments"
    bl_description = "Explicitly save all assignments to disk"

    def execute(self, context):
        # No-op: assignments are saved automatically on set/clear
        self.report({'INFO'}, "Assignments saved")
        return {'FINISHED'}


# -----------------------------------------------------------------------------
# Registration API

def register():
    for cls in (IDS_OT_assign_open, IDS_OT_assign_set, IDS_OT_assign_clear, IDS_OT_assign_save):
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed((IDS_OT_assign_open, IDS_OT_assign_set, IDS_OT_assign_clear, IDS_OT_assign_save)):
        bpy.utils.unregister_class(cls)