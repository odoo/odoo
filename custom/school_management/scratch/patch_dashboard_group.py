with open("addons/spreadsheet_dashboard/data/dashboard.xml", "r", encoding="utf-8") as f:
    c = f.read()

target = """    <record id="spreadsheet_dashboard_group_sales" model="spreadsheet.dashboard.group">
        <field name="name">Sales</field>
        <field name="sequence">100</field>
    </record>"""

replacement = """    <record id="spreadsheet_dashboard_group_sales" model="spreadsheet.dashboard.group">
        <field name="name">Sales</field>
        <field name="sequence">100</field>
    </record>

    <record id="spreadsheet_dashboard_group_education" model="spreadsheet.dashboard.group">
        <field name="name">Education &amp; Academic Management</field>
        <field name="sequence">200</field>
    </record>"""

if "spreadsheet_dashboard_group_education" not in c and target in c:
    c = c.replace(target, replacement, 1)
    with open("addons/spreadsheet_dashboard/data/dashboard.xml", "w", encoding="utf-8") as f:
        f.write(c)
    print("SUCCESS: Added spreadsheet_dashboard_group_education to addons/spreadsheet_dashboard/data/dashboard.xml")
else:
    print("Already present or target not found")
