# -*- coding: utf-8 -*-
"""
ui.py (템플릿)

역할:
    - Blender UI 패널을 정의하여 IDS 애드온의 버튼 및 속성 리스트를 제공한다.
    - View3D > Sidebar > IDS 탭에서 노출된다.

주요 요소:
    - 두 개의 Operator 버튼: [속성 생성], [자동채움 실행]을 배치한다.
    - 선택된 객체의 커스텀 프로퍼티를 표 형태로 보여주며, 사용자가 직접 값을 편집할 수 있게 한다.
    - 내부 키(`_RNA_UI` 등)나 시스템 프로퍼티는 숨긴다.

주의:
    - draw() 메서드에서는 어떤 데이터도 쓰지 않는다. 읽기와 UI 표시에만 집중한다.
    - 오퍼레이터를 실행할 때는 반드시 사용자 이벤트에 의해 실행되어야 한다.
"""

import bpy
from bpy.types import Panel


class IDS_PT_panel(Panel):
    """IDS 패널 클래스이다. Blender UI에서 IDS 탭에 표시된다."""

    bl_label = "IDS"
    bl_idname = "IDS_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'IDS'

    def draw(self, context):
        layout = self.layout
        obj = context.active_object

        # 상단 버튼: 속성 생성 / 자동채움 실행
        row = layout.row(align=True)
        row.operator("ids.create_props", icon="PLUS")
        row.operator("ids.autofill_props", icon="MOD_PHYSICS")

        layout.separator()

        # 현재 선택 오브젝트 정보
        if not obj:
            layout.label(text="오브젝트를 선택하라")
            return

        layout.label(text=f"선택: {obj.name}")

        # 커스텀 프로퍼티 표시
        # Blender 내부 예약키('_RNA_UI' 등)와 내부 타입은 숨긴다.
        shown = 0
        for k in sorted(obj.keys()):
            # 내부 예약키는 건너뜀
            if k.startswith("_"):
                continue
            try:
                layout.prop(obj, f'["{k}"]', text=k)
                shown += 1
            except Exception:
                # 표시 불가능한 타입은 무시한다
                pass

        if shown == 0:
            layout.label(text="표시할 커스텀 속성이 없다(먼저 [속성 생성])")