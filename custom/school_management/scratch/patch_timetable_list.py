with open('c:/Odoo/odoo/custom/school_management/views/timetable_views.xml', 'r', encoding='utf-8') as f:
    content = f.read()

target_list = '''    <record id="view_university_timetable_slot_tree" model="ir.ui.view">
        <field name="name">university.timetable.slot.tree</field>
        <field name="model">university.timetable.slot</field>
        <field name="arch" type="xml">
            <list limit="10" string="Scheduled Sessions" default_order="start_datetime desc" sample="1">
                <header>
                    <button name="%(school_management.action_university_timetable_generation_wizard)d"
                            string="Generate Timetable"
                            type="action"
                            class="btn-primary"
                            icon="fa-magic"
                            groups="school_management.group_school_admin,school_management.group_school_timetable_manager,school_management.group_school_hod"/>
                </header>
                <field name="name" string="Session Code" decoration-bf="1"/>
                <field name="subject_id" string="Subject"/>
                <field name="section_id" string="Section"/>
                <field name="academic_year_id"/>
                <field name="semester_id"/>
                <field name="start_datetime" widget="datetime"/>
                <field name="end_time" widget="datetime"/>
                <field name="room_id" string="Room"/>
                <field name="teacher_user_id" column_invisible="1"/>
                <field name="can_view_session_details" column_invisible="1"/>
                <field name="instructor_id" string="Instructor" invisible="teacher_user_id != uid and not can_view_session_details"/>
                <field name="students_display" string="Students" class="text-end" invisible="teacher_user_id != uid and not can_view_session_details"/>
                <field name="status" widget="badge" 
                       decoration-success="status == 'completed'" 
                       decoration-warning="status == 'ongoing'"
                       decoration-info="status == 'upcoming'"
                       decoration-danger="status == 'cancelled'"/>
                <field name="year_level" optional="hide"/>
                <field name="session_date" optional="hide"/>
                <field name="conflict_indicator" string="Conflict" widget="badge" optional="show"
                       decoration-danger="conflict_indicator == 'conflict'" invisible="not has_conflict"/>
                <field name="room_change_indicator" string="Room Changed" widget="badge" optional="show"
                       decoration-warning="room_change_indicator == 'changed'" invisible="not is_room_changed"/>
                <field name="has_conflict" invisible="1"/>
                <field name="is_room_changed" invisible="1"/>
            </list>
        </field>
    </record>'''

replacement_list = '''    <record id="view_university_timetable_slot_tree" model="ir.ui.view">
        <field name="name">university.timetable.slot.tree</field>
        <field name="model">university.timetable.slot</field>
        <field name="arch" type="xml">
            <list string="Scheduled Sessions"
                  default_order="session_date desc, start_datetime desc"
                  multi_edit="1"
                  sample="1"
                  decoration-danger="has_conflict"
                  decoration-muted="state == 'cancelled'"
                  decoration-warning="is_room_changed">
                <header>
                    <button name="action_publish"
                            string="Publish Selected"
                            type="object"
                            class="btn-primary"
                            groups="school_management.group_school_admin,school_management.group_school_timetable_manager,school_management.group_school_hod"/>
                    <button name="action_set_draft"
                            string="Set to Draft"
                            type="object"
                            class="btn-secondary"
                            groups="school_management.group_school_admin,school_management.group_school_timetable_manager,school_management.group_school_hod"/>
                    <button name="%(school_management.action_university_timetable_generation_wizard)d"
                            string="Generate Timetable"
                            type="action"
                            class="btn-secondary"
                            icon="fa-magic"
                            groups="school_management.group_school_admin,school_management.group_school_timetable_manager,school_management.group_school_hod"/>
                </header>
                <field name="session_date" string="Date" widget="date" decoration-bf="1"/>
                <field name="name" string="Session Code" optional="show"/>
                <field name="resource_id" string="Resource" widget="many2one_avatar" optional="show"/>
                <field name="instructor_id" string="Instructor" widget="many2one_avatar" optional="hide"/>
                <field name="subject_id" string="Subject" class="fw-bold"/>
                <field name="section_id" string="Class / Section"/>
                <field name="academic_year_id" optional="hide"/>
                <field name="semester_id" optional="hide"/>
                <field name="start_datetime" string="Start" widget="datetime"/>
                <field name="end_datetime" string="End" widget="datetime"/>
                <field name="allocated_hours" string="Hours" widget="float_time" sum="Total Hours"/>
                <field name="room_id" string="Room"/>
                <field name="enrolled_student_count" string="Students" class="text-end" optional="show"/>
                <field name="room_capacity" string="Capacity" class="text-end" optional="hide"/>
                <field name="generation_state" string="Publish Status" widget="badge" 
                       decoration-warning="generation_state == 'draft'" 
                       decoration-success="generation_state == 'published'"
                       decoration-danger="generation_state == 'cancelled'"/>
                <field name="status" string="Schedule Status" widget="badge" 
                       decoration-success="status == 'completed'" 
                       decoration-warning="status == 'ongoing'"
                       decoration-info="status == 'upcoming'"
                       decoration-danger="status == 'cancelled'"/>
                <field name="state" string="State" widget="badge" optional="hide"
                       decoration-info="state == 'draft'"
                       decoration-success="state == 'confirmed'"
                       decoration-muted="state == 'cancelled'"/>
                <field name="year_level" optional="hide"/>
                <field name="conflict_indicator" string="Conflict" widget="badge" optional="show"
                       decoration-danger="conflict_indicator == 'conflict'" invisible="not has_conflict"/>
                <field name="room_change_indicator" string="Room Changed" widget="badge" optional="hide"
                       decoration-warning="room_change_indicator == 'changed'" invisible="not is_room_changed"/>
                <button name="action_track_attendance" type="object" string="Attendance" icon="fa-calendar-check-o" 
                        class="btn btn-sm btn-outline-success" invisible="status == 'cancelled'" 
                        groups="school_management.group_school_teacher,school_management.group_school_admin"/>
                <field name="has_conflict" column_invisible="1"/>
                <field name="is_room_changed" column_invisible="1"/>
                <field name="teacher_user_id" column_invisible="1"/>
                <field name="can_view_session_details" column_invisible="1"/>
            </list>
        </field>
    </record>'''

content_norm = content.replace('\r\n', '\n')
target_list_norm = target_list.replace('\r\n', '\n')
assert target_list_norm in content_norm, 'Target not found!'
content_norm = content_norm.replace(target_list_norm, replacement_list.replace('\r\n', '\n'), 1)

target_search = '''            <search string="Search Scheduled Sessions">
                <field name="subject_id"/>
                <field name="section_code"/>
                <field name="section_id" string="Class"/>
                <field name="instructor_id"/>
                <field name="room_id"/>
                <separator/>'''

replacement_search = '''            <search string="Search Scheduled Sessions">
                <field name="subject_id"/>
                <field name="section_code"/>
                <field name="section_id" string="Class"/>
                <field name="resource_id" string="Resource"/>
                <field name="instructor_id"/>
                <field name="room_id"/>
                <separator/>
                <filter string="Draft (Unpublished)" name="filter_draft" domain="[('generation_state', '=', 'draft')]"/>
                <filter string="Published" name="filter_published" domain="[('generation_state', '=', 'published')]"/>
                <separator/>'''

target_search_norm = target_search.replace('\r\n', '\n')
assert target_search_norm in content_norm, 'Target search not found!'
content_norm = content_norm.replace(target_search_norm, replacement_search.replace('\r\n', '\n'), 1)

target_act = '''    <!-- Standard Act Window for backend management -->
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
    </record>'''

replacement_act = '''    <!-- Standard Act Window for backend management -->
    <record id="action_university_timetable_slot" model="ir.actions.act_window">
        <field name="name">Schedule by Resource</field>
        <field name="res_model">university.timetable.slot</field>
        <field name="view_mode">gantt,kanban,list,form</field>
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

    <record id="action_university_timetable_slot_view_kanban" model="ir.actions.act_window.view">
        <field name="sequence" eval="2"/>
        <field name="view_mode">kanban</field>
        <field name="view_id" ref="view_university_timetable_slot_kanban"/>
        <field name="act_window_id" ref="action_university_timetable_slot"/>
    </record>

    <record id="action_university_timetable_slot_view_list" model="ir.actions.act_window.view">
        <field name="sequence" eval="3"/>
        <field name="view_mode">list</field>
        <field name="view_id" ref="view_university_timetable_slot_tree"/>
        <field name="act_window_id" ref="action_university_timetable_slot"/>
    </record>

    <record id="action_university_timetable_slot_view_form" model="ir.actions.act_window.view">
        <field name="sequence" eval="4"/>
        <field name="view_mode">form</field>
        <field name="view_id" ref="view_university_timetable_slot_form"/>
        <field name="act_window_id" ref="action_university_timetable_slot"/>
    </record>'''

target_act_norm = target_act.replace('\r\n', '\n')
assert target_act_norm in content_norm, 'Target act not found!'
content_norm = content_norm.replace(target_act_norm, replacement_act.replace('\r\n', '\n'), 1)

with open('c:/Odoo/odoo/custom/school_management/views/timetable_views.xml', 'w', encoding='utf-8') as f:
    f.write(content_norm)

print('Updated timetable_views.xml successfully!')
