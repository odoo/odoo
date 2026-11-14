import os

views_file = "custom/school_management/views/timetable_views.xml"
with open(views_file, "r", encoding="utf-8") as f:
    xml = f.read()

# 1. Add group_by_resource in search view if not present
if 'name="group_by_resource"' not in xml:
    xml = xml.replace(
        '<filter string="Room" name="group_by_room"',
        '<filter string="Resources" name="group_by_resource" context="{\'group_by\': \'resource_id\'}"/>\n                    <filter string="Room" name="group_by_room"',
        1
    )

# 2. Add gantt view definition and update actions
gantt_view_xml = """    <!-- Schedule by Resource Gantt View (Odoo 19 Syntax) -->
    <record id="view_university_timetable_slot_gantt" model="ir.ui.view">
        <field name="name">university.timetable.slot.gantt</field>
        <field name="model">university.timetable.slot</field>
        <field name="arch" type="xml">
            <gantt date_start="start_datetime"
                   date_stop="end_datetime"
                   default_group_by="resource_id"
                   scale="week"
                   color="color"
                   string="Schedule by Resource">
                <field name="name"/>
                <field name="resource_id"/>
                <field name="start_datetime"/>
                <field name="end_datetime"/>
                <field name="allocated_hours"/>
                <field name="color"/>
                <field name="state"/>
                <templates>
                    <div t-name="gantt-pill">
                        <t t-esc="pill_text"/>
                    </div>
                </templates>
            </gantt>
        </field>
    </record>

    <!-- Unified OWL Schedule Client Action -->
    <record id="action_university_schedule_view" model="ir.actions.client">
        <field name="name">Schedule by Resource</field>
        <field name="tag">university_schedule_gantt</field>
        <field name="target">main</field>
        <field name="context">{'default_view_mode': 'week'}</field>
    </record>

    <!-- Standard Act Window for backend management -->
    <record id="action_university_timetable_slot" model="ir.actions.act_window">
        <field name="name">Schedule by Resource</field>
        <field name="res_model">university.timetable.slot</field>
        <field name="view_mode">gantt,list,form</field>
        <field name="view_id" ref="view_university_timetable_slot_gantt"/>
        <field name="search_view_id" ref="view_university_timetable_slot_search"/>
        <field name="context">{'search_default_group_by_resource': 1, 'search_default_active_sessions': 1}</field>
        <field name="limit">80</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">No schedules planned for this week.</p>
        </field>
    </record>

    <record id="action_university_timetable_slot_view_gantt" model="ir.actions.act_window.view">
        <field name="sequence" eval="1"/>
        <field name="view_mode">gantt</field>
        <field name="view_id" ref="view_university_timetable_slot_gantt"/>
        <field name="act_window_id" ref="action_university_timetable_slot"/>
    </record>

    <record id="action_university_timetable_slot_view_list" model="ir.actions.act_window.view">
        <field name="sequence" eval="2"/>
        <field name="view_mode">list</field>
        <field name="view_id" ref="view_university_timetable_slot_tree"/>
        <field name="act_window_id" ref="action_university_timetable_slot"/>
    </record>

    <record id="action_university_timetable_slot_view_form" model="ir.actions.act_window.view">
        <field name="sequence" eval="3"/>
        <field name="view_mode">form</field>
        <field name="view_id" ref="view_university_timetable_slot_form"/>
        <field name="act_window_id" ref="action_university_timetable_slot"/>
    </record>
"""

# Replace the old action_university_schedule_view and action_university_timetable_slot block
old_block_start = '    <!-- Unified OWL Schedule Client Action -->'
old_block_end = '    <!-- Legacy Action preserved, now defaulting to published slots -->'

start_idx = xml.find(old_block_start)
end_idx = xml.find(old_block_end)

if start_idx != -1 and end_idx != -1:
    xml = xml[:start_idx] + gantt_view_xml + "\n\n" + xml[end_idx:]
    print("Replaced actions block with Gantt view and actions")
else:
    print("Warning: old block markers not found")

with open(views_file, "w", encoding="utf-8") as f:
    f.write(xml)
print("Updated timetable_views.xml successfully")
