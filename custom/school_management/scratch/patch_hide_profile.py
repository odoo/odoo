with open('c:/Odoo/odoo/custom/school_management/models/timetable.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _filter_visible_menus(self):
        res = super()._filter_visible_menus()
        user = self.env.user
        # Remove "My Timetable" from Admin Schedule menu
        if user.has_group("school_management.group_school_admin") or self.env.is_system():
            my_timetable = self.env.ref("school_management.menu_university_timetable_teacher", raise_if_not_found=False)
            if my_timetable and my_timetable in res:
                res = res - my_timetable
        return res'''

replacement = '''class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        user = self.env.user
        if user.has_group("school_management.group_school_admin") or self.env.is_system():
            hidden_xml_ids = [
                "school_management.menu_teacher_nav_profile",
                "school_management.menu_student_nav_profile",
                "school_management.menu_university_timetable_teacher",
            ]
            blacklisted = []
            for xml_id in hidden_xml_ids:
                menu = self.env.ref(xml_id, raise_if_not_found=False)
                if menu:
                    blacklisted.append(menu.id)
            return list(set(res + blacklisted))
        return res

    def _filter_visible_menus(self):
        res = super()._filter_visible_menus()
        user = self.env.user
        # Remove "My Profile" and "My Timetable" from Admin menus
        if user.has_group("school_management.group_school_admin") or self.env.is_system():
            hidden_xml_ids = [
                "school_management.menu_teacher_nav_profile",
                "school_management.menu_student_nav_profile",
                "school_management.menu_university_timetable_teacher",
            ]
            to_remove = self.browse()
            for xml_id in hidden_xml_ids:
                menu = self.env.ref(xml_id, raise_if_not_found=False)
                if menu and menu in res:
                    to_remove |= menu
            if to_remove:
                res = res - to_remove
        return res'''

content_norm = content.replace('\r\n', '\n')
target_norm = target.replace('\r\n', '\n')
assert target_norm in content_norm, 'Target not found in timetable.py'
content_norm = content_norm.replace(target_norm, replacement.replace('\r\n', '\n'), 1)

with open('c:/Odoo/odoo/custom/school_management/models/timetable.py', 'w', encoding='utf-8') as f:
    f.write(content_norm)

print('Updated timetable.py successfully!')

# Now update menu_views.xml
with open('c:/Odoo/odoo/custom/school_management/views/menu_views.xml', 'r', encoding='utf-8') as f:
    mcontent = f.read()

mtarget = '''    <!-- Teacher/student profile; administrators do not get a self-service profile menu. -->
    <record id="menu_teacher_nav_profile" model="ir.ui.menu">
        <field name="name">My Profile</field>
        <field name="parent_id" ref="menu_school_root"/>
        <field name="action" ref="action_open_university_teacher_profile"/>
        <field name="sequence">95</field>
        <field name="group_ids" eval="[(6, 0, [ref('school_management.group_school_teacher'), ref('school_management.group_school_student')])]"/>
    </record>'''

mreplacement = '''    <!-- Teacher profile; administrators do not get a self-service profile menu. -->
    <record id="menu_teacher_nav_profile" model="ir.ui.menu">
        <field name="name">My Profile</field>
        <field name="parent_id" ref="menu_school_root"/>
        <field name="action" ref="action_open_university_teacher_profile"/>
        <field name="sequence">95</field>
        <field name="group_ids" eval="[(6, 0, [ref('school_management.group_school_teacher')])]"/>
    </record>'''

mcontent_norm = mcontent.replace('\r\n', '\n')
mtarget_norm = mtarget.replace('\r\n', '\n')
assert mtarget_norm in mcontent_norm, 'Target not found in menu_views.xml'
mcontent_norm = mcontent_norm.replace(mtarget_norm, mreplacement.replace('\r\n', '\n'), 1)

with open('c:/Odoo/odoo/custom/school_management/views/menu_views.xml', 'w', encoding='utf-8') as f:
    f.write(mcontent_norm)

print('Updated menu_views.xml successfully!')

# Update security.xml
with open('c:/Odoo/odoo/custom/school_management/security/security.xml', 'r', encoding='utf-8') as f:
    scontent = f.read()

starget = '''    <record id="group_school_timetable_manager" model="res.groups">
        <field name="name">Timetable Manager</field>
        <field name="privilege_id" ref="school_management_privilege"/>
        <field name="implied_ids" eval="[(4, ref('group_school_teacher'))]"/>
    </record>'''

sreplacement = '''    <record id="group_school_timetable_manager" model="res.groups">
        <field name="name">Timetable Manager</field>
        <field name="privilege_id" ref="school_management_privilege"/>
        <field name="implied_ids" eval="[(4, ref('group_school_user'))]"/>
    </record>'''

scontent_norm = scontent.replace('\r\n', '\n')
starget_norm = starget.replace('\r\n', '\n')
assert starget_norm in scontent_norm, 'Target not found in security.xml'
scontent_norm = scontent_norm.replace(starget_norm, sreplacement.replace('\r\n', '\n'), 1)

with open('c:/Odoo/odoo/custom/school_management/security/security.xml', 'w', encoding='utf-8') as f:
    f.write(scontent_norm)

print('Updated security.xml successfully!')
