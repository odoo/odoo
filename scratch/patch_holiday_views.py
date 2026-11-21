with open("custom/school_public_holiday/views/public_holiday_views.xml", "r", encoding="utf-8") as f:
    content = f.read()

target = '''<odoo>
    <!-- EXTEND FORM VIEW -->'''

replacement = '''<odoo>
    <record id="action_wizard_import_public_holiday" model="ir.actions.act_window">
        <field name="name">Import Public Holidays</field>
        <field name="res_model">wizard.import.public.holiday</field>
        <field name="view_mode">form</field>
        <field name="target">new</field>
    </record>

    <!-- EXTEND FORM VIEW -->'''

assert target in content, "target not found"
new_content = content.replace(target, replacement, 1)
with open("custom/school_public_holiday/views/public_holiday_views.xml", "w", encoding="utf-8") as f:
    f.write(new_content)
print("public_holiday_views.xml updated")
