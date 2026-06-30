<?xml version='1.0' encoding='UTF-8' ?>
<odoo>
    <record id="l10n_in_hr_leave_optional_holiday_view_list" model="ir.ui.view">
        <field name="model">l10n.in.hr.leave.optional.holiday</field>
        <field name="arch" type="xml">
            <list editable="bottom">
                <field name="name"/>
                <field name="date" string="Date"/>
                <field name="company_id" string="Company" groups="base.group_multi_company"/>
            </list>
        </field>
    </record>

    <record id="l10n_in_hr_leave_optional_holiday_view_search" model="ir.ui.view">
        <field name="model">l10n.in.hr.leave.optional.holiday</field>
        <field name="arch" type="xml">
            <search string="Optional Holidays">
                <field name="name"/>
                <field name="date" string="Start Date"/>
                <field name="company_id" string="Company" groups="base.group_multi_company"/>
                <separator/>
                <filter name="filter_date" date="date" default_period="year" string="Period"/>
                <group>
                    <filter name="company" string="Company" context="{'group_by': 'company_id'}"
                        groups="base.group_multi_company"/>
                </group>
            </search>
        </field>
    </record>

    <record id="l10n_in_hr_leave_optional_holiday_action" model="ir.actions.act_window">
        <field name="name">Optional Holidays</field>
        <field name="res_model">l10n.in.hr.leave.optional.holiday</field>
        <field name="view_mode">list</field>
        <field name="context">{'search_default_filter_date': True}</field>
    </record>

    <menuitem
        id="l10n_in_menu_optional_holiday_configuration"
        action="l10n_in_hr_leave_optional_holiday_action"
        name="Optional Holidays"
        parent="hr_holidays.menu_hr_holidays_configuration"
        groups="hr_holidays.group_hr_holidays_manager"
        sequence="5"/>
</odoo>
