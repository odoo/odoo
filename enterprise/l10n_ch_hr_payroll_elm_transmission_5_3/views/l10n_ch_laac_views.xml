<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="l10n_ch_additional_accident_insurance_line_view_form" model="ir.ui.view">
        <field name="name">l10n.ch.additional.accident.insurance.line.view.form</field>
        <field name="model">l10n.ch.additional.accident.insurance.line</field>
        <field name="inherit_id" ref="l10n_ch_hr_payroll.l10n_ch_additional_accident_insurance_line_view_form"/>
        <field name="arch" type="xml">
            <form position="replace">
                <form>
                    <group>
                        <group>
                            <field name="solution_name"/>
                            <field name="solution_type"/>
                            <field name="solution_number"/>
                        </group>
                        <field name="rate_ids" nolabel="1" colspan="2">
                            <list>
                                <field name="date_from"/>
                                <field name="date_to"/>
                                <field name="wage_from"/>
                                <field name="wage_to"/>
                            </list>
                            <form>
                                <sheet>
                                    <group>
                                        <group>
                                            <field name="date_from"/>
                                            <field name="date_to"/>
                                            <label for="wage_from"/>
                                            <div class="o_row o_hr_narrow_field">
                                                <field name="wage_from" nolabel="1"/>
                                                <span>CHF</span>
                                            </div>
                                            <label for="wage_to"/>
                                            <div class="o_row o_hr_narrow_field">
                                                <field name="wage_to" nolabel="1"/>
                                                <span>CHF</span>
                                            </div>
                                            <field name="custom_employer_rates"/>
                                        </group>
                                        <group>
                                            <field name="male_rate"/>
                                            <field name="female_rate"/>
                                            <field name="employer_part" invisible="custom_employer_rates"/>
                                            <field name="employer_rate_male" invisible="not custom_employer_rates"/>
                                            <field name="employer_rate_female" invisible="not custom_employer_rates"/>
                                        </group>
                                    </group>
                                </sheet>
                            </form>
                        </field>
                </group>
            </form>
            </form>
        </field>
    </record>
</odoo>
