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
