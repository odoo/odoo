# -*- coding: utf-8 -*-
from odoo import api, fields, models

MODULE = "npi_optometrist_search"


class ExternalProvider(models.Model):
    _name = "external.provider"
    _description = "External Provider"
    _order = "name"

    name = fields.Char(string="Name")
    phone = fields.Char(string="Phone")
    email = fields.Char(string="Email")
    address_1 = fields.Char(string="Address 1")
    address_2 = fields.Char(string="Address 2")
    city = fields.Char(string="City")
    state = fields.Char(string="State", size=2)
    postal_code = fields.Char(string="Postal Code")
    npi = fields.Char(string="NPI", index=True)
    company = fields.Char(string="Company")
    license = fields.Char(string="License")
    taxonomy = fields.Char(string="Taxonomy")
    manual_entry = fields.Boolean(string="Manual entry", default=False, help="True when form opened from Manual button (hide NPI search section).")

    def action_delete_and_redirect(self):
        """Delete record(s) and return action to open External Provider (so client redirects)."""
        self.unlink()
        return {
            "type": "ir.actions.act_window",
            "name": "External Provider",
            "res_model": "external.provider",
            "view_mode": "kanban,list,form",
            "target": "current",
        }

    @api.model
    def _add_address_views(self):
        """Update External Provider views to include address fields (runs after data load on upgrade)."""
        View = self.env["ir.ui.view"]
        list_view = self.env.ref("%s.view_external_provider_list" % MODULE, raise_if_not_found=False)
        form_view = self.env.ref("%s.view_external_provider_form" % MODULE, raise_if_not_found=False)
        list_arch = """<list string="External Provider" create="1" edit="1" delete="1" limit="5">
                <field name="name"/>
                <field name="phone"/>
                <field name="email"/>
                <field name="address_1"/>
                <field name="city"/>
                <field name="state"/>
                <field name="postal_code"/>
                <field name="npi"/>
                <field name="company"/>
                <field name="license"/>
                <field name="taxonomy"/>
            </list>"""
        form_arch = """<form string="External Provider">
                <sheet>
                    <group string="New" colspan="2" invisible="manual_entry or id">
                        <div class="alert alert-info mb-0" role="alert">
                            <p class="mb-2">Search the NPI Registry to add a provider, or click Manual in the search dialog to enter manually.</p>
                            <button name="%(action)s" type="action" string="Search NPI Registry" class="btn-primary"/>
                        </div>
                    </group>
                    <group>
                        <group string="Provider Info">
                            <field name="manual_entry" invisible="1"/>
                            <field name="name"/>
                            <field name="phone"/>
                            <field name="email"/>
                            <field name="company"/>
                            <field name="npi"/>
                            <field name="license"/>
                            <field name="taxonomy"/>
                        </group>
                        <group string="Address">
                            <field name="address_1"/>
                            <field name="address_2"/>
                            <field name="city"/>
                            <field name="state"/>
                            <field name="postal_code"/>
                        </group>
                    </group>
                </sheet>
                <footer>
                    <button name="action_delete_and_redirect" string="Delete" type="object" class="btn-danger"/>
                </footer>
            </form>""" % {"action": "npi_optometrist_search.action_npi_optometrist_search"}
        if list_view:
            list_view.write({"arch": list_arch})
        if form_view:
            form_view.write({"arch": form_arch})
        # Also add npi_number to NPI search form (so upgrade validates without it in XML)
        search_form = self.env.ref(
            "%s.view_npi_optometrist_search_form" % MODULE,
            raise_if_not_found=False,
        )
        if search_form:
            search_form.write({
                "arch": """<form string="Search Eye Care Providers">
                <sheet>
                    <group>
                        <group string="Search Criteria">
                            <field name="npi_number" placeholder="e.g., 1902992886"/>
                            <field name="first_name" placeholder="e.g., John or Jo*"/>
                            <field name="last_name" placeholder="e.g., Smith or Sm*"/>
                            <field name="state" placeholder="e.g., CA, UT"/>
                            <field name="city"/>
                            <field name="postal_code"/>
                            <field name="limit"/>
                        </group>
                        <group string="Info">
                            <div class="alert alert-info" role="alert">
                                <p>Searches the NPPES NPI Registry for <strong>optometrists, ophthalmologists, ophthalmology, and opticians</strong>.</p>
                                <p>Search by <strong>NPI number</strong> for a specific provider, or use name, state, city, or postal code.</p>
                                <p>Use * for wildcard (e.g., last_name="Smi*").</p>
                            </div>
                        </group>
                    </group>
                    <notebook invisible="not result_ids">
                        <page string="Results" name="results">
                            <field name="result_ids" nolabel="1">
                                <kanban string="Eye Care Providers" create="false" delete="false" edit="false">
                                    <field name="taxonomy_desc"/>
                                    <field name="npi_number"/>
                                    <field name="name"/>
                                    <field name="credential"/>
                                    <field name="address_1"/>
                                    <field name="city"/>
                                    <field name="state"/>
                                    <field name="postal_code"/>
                                    <templates>
                                        <t t-name="card" class="o_kanban_card">
                                            <div class="oe_kanban_content">
                                                <div class="o_kanban_record_top">
                                                    <span class="badge text-bg-secondary mb-1"><field name="taxonomy_desc"/></span>
                                                    <strong class="o_kanban_record_title d-block"><field name="name"/></strong>
                                                    <span t-if="record.credential.raw_value" class="text-muted">(<field name="credential"/>)</span>
                                                </div>
                                                <div class="o_kanban_record_body mt-2">
                                                    <div><i class="fa fa-id-card me-1"/> NPI: <field name="npi_number"/></div>
                                                    <div t-if="record.address_1.raw_value"><i class="fa fa-map-marker me-1"/><field name="address_1"/></div>
                                                    <div t-if="record.city.raw_value or record.state.raw_value">
                                                        <field name="city"/><t t-if="record.state.raw_value">, </t><field name="state"/><t t-if="record.postal_code.raw_value"> </t><field name="postal_code"/>
                                                    </div>
                                                    <div t-if="record.taxonomy_desc.raw_value" class="text-muted small mt-1"><field name="taxonomy_desc"/></div>
                                                </div>
                                                <div class="mt-2">
                                                    <button name="npi_optometrist_search.action_import_npi_result" type="action" class="btn btn-primary btn-sm">Import</button>
                                                </div>
                                            </div>
                                        </t>
                                    </templates>
                                </kanban>
                            </field>
                        </page>
                    </notebook>
                </sheet>
                <footer>
                    <button name="action_search" string="Search" type="object" class="btn-primary"/>
                    <button name="action_manual" string="Manual" type="object" class="btn-secondary"/>
                    <button string="Close" class="btn-secondary" special="cancel"/>
                </footer>
            </form>"""
            })
