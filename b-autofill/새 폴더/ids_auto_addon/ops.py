# -*- coding: utf-8 -*-
"""
ops.py (템플릿)

역할:
    - Blender Operator 클래스를 정의한다. 사용자가 IDS 자동 생성 애드온을 통해
      Pset.Property 키를 생성하고 값 자동 채움을 수행하는 버튼을 제공한다.
    - 속성 생성(create) 오퍼레이터와 자동 채움(autofill) 오퍼레이터가 있다.

특징:
    - parser 모듈을 활용하여 현재 오브젝트에 해당하는 IDS 요구사항을 가져온다.
    - ifcopenshell을 사용하여 GlobalId 기반 매칭을 수행한 뒤, Blender 객체 이름 기반
      매칭도 병행한다. parser.iter_requirements_for_object()에 이 로직이 구현되어 있다.
    - methods.autofill_value()를 호출하여 method=b/c/d에 따른 값을 계산하고,
      dtype에 맞추어 캐스팅 후 커스텀 프로퍼티에 기록한다.

제한사항:
    - 본 애드온은 method=b (지오메트리 기반) 자동채움만 동작하도록 설계된다.
    - 검증 및 리포트 기능은 포함하지 않는다.
    - IFC 파일에 직접 쓰거나 수정하는 기능은 포함하지 않는다.
"""

import bpy
from bpy.types import Operator

from . import parser
from .methods import autofill_value


def _get_selected_objects(context):
    """선택된 객체 리스트를 반환한다. 아무 것도 선택되지 않았으면 active_object를 사용한다."""
    objs = list(context.selected_objects) if context.selected_objects else []
    if not objs and context.active_object:
        objs = [context.active_object]
    return objs


def _get_initial_value(prop_conf):
    """Property 설정 dict에서 초기값을 계산한다.

    dtype 힌트에 따라 기본값을 생성하며, default 값이 명시되어 있으면 이를 우선 사용한다.
    """
    dtype = (prop_conf.get("dtype") or "").strip().lower()
    default = prop_conf.get("default")
    if default is not None:
        return default
    # dtype에 따른 기본값
    if dtype == "number":
        return 0.0
    if dtype == "bool":
        return False
    # 그 외는 문자열
    return ""


class IDS_OT_create_props(Operator):
    """IDS 요구사항에 따라 Pset.Property 커스텀 프로퍼티를 생성한다."""

    bl_idname = "ids.create_props"
    bl_label = "속성 생성"
    bl_description = "선택 객체에 IDS에서 요구하는 Pset.Property를 생성한다 (중복 생성 방지)."

    def execute(self, context):
        objs = _get_selected_objects(context)
        if not objs:
            self.report({'WARNING'}, "선택된 오브젝트가 없다")
            return {'CANCELLED'}
        created_total = 0
        # 각 오브젝트별로 IDS 요구사항을 가져와 속성을 생성한다.
        for obj in objs:
            # 매칭되는 요구사항 탐색
            for req in parser.iter_requirements_for_object(obj):
                pset = req.get("pset") or ""
                for pconf in req.get("properties", []):
                    key = f"{pset}.{pconf.get('name')}"
                    # 이미 속성이 있으면 건너뛴다
                    if key in obj.keys():
                        continue
                    # 초기값 지정
                    obj[key] = _get_initial_value(pconf)
                    created_total += 1
        self.report({'INFO'}, f"생성된 속성 수: {created_total}")
        return {'FINISHED'}


class IDS_OT_autofill_props(Operator):
    """method=b/c/d인 속성에 대해 자동으로 값을 채워 넣는다."""

    bl_idname = "ids.autofill_props"
    bl_label = "자동채움 실행"
    bl_description = "선택 객체의 method=b/c/d 속성에 대해 값을 자동 계산하여 채운다. A는 수동."

    def execute(self, context):
        objs = _get_selected_objects(context)
        if not objs:
            self.report({'WARNING'}, "선택된 오브젝트가 없다")
            return {'CANCELLED'}
        filled_total = 0
        # 모든 선택된 객체에 대해 수행
        for obj in objs:
            # 매칭 요구사항 순회
            for req in parser.iter_requirements_for_object(obj):
                pset = req.get("pset") or ""
                for pconf in req.get("properties", []):
                    method_tag = (pconf.get("method") or "a").lower()
                    # 자동채움 대상은 b/c/d만 해당된다
                    if method_tag == "a":
                        continue
                    key = f"{pset}.{pconf.get('name')}"
                    # 존재하지 않으면 속성을 생성한다
                    if key not in obj.keys():
                        obj[key] = _get_initial_value(pconf)
                    # 값 계산
                    val = autofill_value(obj, method_tag, key)
                    if val is None:
                        continue
                    # dtype 캐스팅: numbers, bool, else string
                    dtype = (pconf.get("dtype") or "").strip().lower()
                    try:
                        if dtype == "number":
                            obj[key] = float(val)
                        elif dtype == "bool":
                            obj[key] = bool(val)
                        else:
                            obj[key] = str(val)
                    except Exception:
                        # 예외 발생 시 문자열로 보관한다
                        obj[key] = str(val)
                    filled_total += 1
        self.report({'INFO'}, f"자동채움 완료: {filled_total}")
        return {'FINISHED'}