<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_form_pos_close_session_wizard" model="ir.ui.view">
        <field name="name">pos.close.session.wizard.form</field>
        <field name="model">pos.close.session.wizard</field>
        <field name="arch" type="xml">
            <form string="Force Close Session">
                <p><field name="message" readonly="1" /></p>
                <group>
                    <field name="account_readonly" invisible="1" />
                    <field name="amount_to_balance" readonly="1" />
                    <field name="account_id" attrs="{'readonly': [('account_readonly', '==', True)]}"/>
                </group>
                <footer>
                    <button name="close_session" string="Close Session" type="object" class="btn-primary" data-hotkey="q"/>
                    <button special="cancel" data-hotkey="z" string="Cancel" class="btn-secondary" />
                </footer>
            </form>
        </field>
    </record>
</odoo>
