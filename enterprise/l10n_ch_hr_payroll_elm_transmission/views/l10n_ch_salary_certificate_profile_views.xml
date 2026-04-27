<?xml version="1.0" encoding="UTF-8"?>
<odoo>
    <record id="view_l10n_ch_salary_certificate_profile_tree" model="ir.ui.view">
        <field name="name">l10n.ch.salary.certificate.profile.tree</field>
        <field name="model">l10n.ch.salary.certificate.profile</field>
        <field name="arch" type="xml">
            <list string="Wage Statements">
                <field name="name"/>
                <field name="company_id" groups="base.group_multi_company"/>
                <field name="l10n_ch_certificate_type"/>
            </list>
        </field>
    </record>

    <record id="view_l10n_ch_salary_certificate_profile_form" model="ir.ui.view">
        <field name="name">l10n.ch.salary.certificate.profile.form</field>
        <field name="model">l10n.ch.salary.certificate.profile</field>
        <field name="arch" type="xml">
            <form string="Wage Statement">
                <header>
                    <button name="action_update_all_certificates" type="object" invisible="employee_id" string="Update All Wage Statements"/>
                </header>
                <sheet>
                    <div class="oe_title">
                        <label for="name"/>
                        <h2>
                            <field name="name" class="oe_inline" placeholder="Wage Statement Name" required="1"/>
                        </h2>
                    </div>
                    <group>
                        <field name="employee_id" invisible="1"/>
                        <field name="certificate_template_id" invisible="not employee_id" required="employee_id"/>
                        <field name="valid_from" invisible="not employee_id"/>
                        <field name="company_id" groups="base.group_multi_company" invisible="employee_id"/>
                    </group>
                    <group invisible="not employee_id">
                        <field name="l10n_ch_certificate_type" widget="radio"/>
                    </group>
                    <group string="Transportation and Meals">
                        <field name="l10n_ch_cs_free_transport"/>
                        <field name="l10n_ch_cs_free_meals"/>
                    </group>
                    <group>

                    <!-- Car Policy and Expense Policy -->
                    <group string="Company Policies">
                        <field name="l10n_ch_cs_car_policy" widget="radio"/>
                        <field name="l10n_ch_cs_expense_policy" widget="radio"/>
                        <field name="l10n_ch_cs_expense_policy_approved_canton" invisible="l10n_ch_cs_expense_policy != 'approved'" required="l10n_ch_cs_expense_policy == 'approved'"/>
                        <field name="l10n_ch_cs_expense_policy_approved_date" invisible="l10n_ch_cs_expense_policy != 'approved'" required="l10n_ch_cs_expense_policy == 'approved'"/>

                        <field name="l10n_ch_cs_expense_expatriate_ruling_approved"/>
                        <field name="l10n_ch_cs_expense_expatriate_ruling_approved_canton" string="Canton" invisible="not l10n_ch_cs_expense_expatriate_ruling_approved" required="l10n_ch_cs_expense_expatriate_ruling_approved"/>
                        <field name="l10n_ch_cs_expense_expatriate_ruling_approved_date" string="Date" invisible="not l10n_ch_cs_expense_expatriate_ruling_approved" required="l10n_ch_cs_expense_expatriate_ruling_approved"/>
                    </group>

                    <!-- Employee Participation -->
                    <group string="Employee Participation">
                        <field name="l10n_ch_cs_employee_parti_fair_market_value"/>
                        <field name="l10n_ch_cs_employee_parti_fair_market_value_canton" string="Canton" invisible="not l10n_ch_cs_employee_parti_fair_market_value" required="l10n_ch_cs_employee_parti_fair_market_value"/>
                        <field name="l10n_ch_cs_employee_parti_fair_market_value_date" string="Date" invisible="not l10n_ch_cs_employee_parti_fair_market_value" required="l10n_ch_cs_employee_parti_fair_market_value"/>

                        <field name="l10n_ch_cs_employee_participation_taxable_income"/>
                        <field name="l10n_ch_cs_employee_participation_taxable_income_locked" invisible="not l10n_ch_cs_employee_participation_taxable_income"/>
                        <field name="l10n_ch_cs_employee_participation_taxable_income_unlisted" invisible="not l10n_ch_cs_employee_participation_taxable_income"/>
                        <field name="l10n_ch_cs_employee_participation_taxable_income_reversional" invisible="not l10n_ch_cs_employee_participation_taxable_income"/>
                        <field name="l10n_ch_cs_employee_participation_taxable_income_virtual" invisible="not l10n_ch_cs_employee_participation_taxable_income"/>
                    </group>
                    </group>

                    <group string="Additional Information" invisible="not certificate_template_id">
                        <field name="l10n_ch_source_tax_settlement_letter"/>
                        <field name="l10n_ch_child_allowance_indirect"/>
                        <field name="l10n_ch_relocation_costs"/>
                        <field name="l10n_ch_provision_salary"/>

                        <field name="l10n_ch_provision_salary_first_name" string="First Name" invisible="not l10n_ch_provision_salary" required="l10n_ch_provision_salary"/>
                        <field name="l10n_ch_provision_salary_last_name" string="Last Name" invisible="not l10n_ch_provision_salary" required="l10n_ch_provision_salary"/>
                        <label for="l10n_ch_provision_salary_street" string="Address" invisible="not l10n_ch_provision_salary"/>
                        <div class="o_address_format" invisible="not l10n_ch_provision_salary">
                            <field name="l10n_ch_provision_salary_street" placeholder="Street..." class="o_address_street"/>
                            <field name="l10n_ch_provision_salary_street2" placeholder="Street 2..." class="o_address_street"/>
                            <field name="l10n_ch_provision_salary_city" placeholder="City" class="o_address_city" required="l10n_ch_provision_salary"/>
                            <field name="l10n_ch_provision_salary_zip" placeholder="ZIP" class="o_address_zip" required="l10n_ch_provision_salary"/>
                            <field name="l10n_ch_provision_salary_country" placeholder="Country" class="o_address_country" options='{"no_open": True, "no_create": True}' required="l10n_ch_provision_salary"/>
                        </div>
                    </group>

                    <group>
                        <field name="l10n_ch_cs_other_fringe_benefits" widget="text" placeholder="Other Fringe Benefits"/>
                        <field name="l10n_ch_cs_additional_text" widget="text" placeholder="Additional Text"/>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <record id="action_l10n_ch_salary_certificate_profile" model="ir.actions.act_window">
        <field name="name">Wage Statement Profile</field>
        <field name="res_model">l10n.ch.salary.certificate.profile</field>
        <field name="view_mode">list,form</field>
        <field name="domain">
            [('certificate_template_id', '=', False)]
        </field>
        <field name="help" type="html">
            <p class="oe_view_nocontent_create">
                Click to create a new salary certificate profile.
            </p>
        </field>
    </record>



</odoo>
