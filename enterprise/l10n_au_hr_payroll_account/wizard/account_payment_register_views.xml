<?xml version="1.0" encoding="utf-8"?>
<odoo>

    <record id="view_account_payment_register_form_inherit" model="ir.ui.view">
        <field name="name">account.payment.register.view.form.inherit</field>
        <field name="model">account.payment.register</field>
        <field name="inherit_id" ref="account.view_account_payment_register_form"/>
        <field name="arch" type="xml">
            <xpath expr="//div[@invisible='not missing_account_partners']" position="after">
                <div role="alert" class="alert alert-warning" invisible="not missing_account_employees">
                    <span class="fw-bold">Payments related to employee(s) with no bank account specified will be skipped. <button class="oe_link p-0 align-baseline" type="object" name="action_open_missing_account_employees">View Employee(s)</button></span>
                </div>
            </xpath>
        </field>
    </record>

</odoo>
