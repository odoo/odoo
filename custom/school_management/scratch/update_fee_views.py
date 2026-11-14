path = r"c:\Odoo\odoo\custom\school_management\views\fee_views.xml"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

target = """                <header>
                    <button name="action_register_payment" string="Register Payment" type="object" invisible="state != 'posted' or balance &lt;= 0" class="oe_highlight btn-success"/>"""

replacement = """                <header>
                    <button name="action_print_invoice" string="Print Invoice" type="object" invisible="state == 'canceled'" class="oe_highlight"/>
                    <button name="action_register_payment" string="Register Payment" type="object" invisible="state != 'posted' or balance &lt;= 0" class="oe_highlight btn-success"/>"""

if target in c:
    c = c.replace(target, replacement, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(c)
    print("Replaced successfully")
else:
    print("Target not found")
