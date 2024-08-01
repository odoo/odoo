from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class AccountFiscalPosition(models.Model):
    _inherit = "account.fiscal.position"

    delivery_country_id = fields.Many2one("res.country", string="Delivery Country", help="Apply only if delivery country matches.")

    @api.model
    def create(self, vals):
        vals = self.adjust_vals_delivery_country_id(vals)
        vals = self.adjust_vals_country_id(vals)
        return super().create(vals)

    def write(self, vals):
        vals = self.adjust_vals_delivery_country_id(vals)
        vals = self.adjust_vals_country_id(vals)
        return super().write(vals)

    def adjust_vals_delivery_country_id(self, vals):
        country_id = self.country_id or vals.get('country_id')
        delivery_country_id = self.delivery_country_id or vals.get('delivery_country_id')
        if not delivery_country_id and country_id:
            vals['delivery_country_id'] = country_id
        return vals

    def adjust_vals_country_id(self, vals):
        foreign_vat = vals.get('foreign_vat')
        country_group_id = vals.get('country_group_id')
        if foreign_vat and country_group_id and not (self.delivery_country_id or vals.get('delivery_country_id')):
            vals['delivery_country_id'] = self.env['res.country.group'].browse(country_group_id).country_ids.filtered(lambda c: c.code == foreign_vat[:2].upper()).id or False
        if not (self.country_id or vals.get('country_id')) and vals.get('delivery_country_id'):
            vals['country_id'] = vals['delivery_country_id']
        return vals

    @api.depends('foreign_vat', 'country_id')
    def _compute_foreign_vat_header_mode(self):
        for record in self:
            if not record.foreign_vat or not (record.country_id or record.delivery_country_id):
                record.foreign_vat_header_mode = None
                continue

            if self.env['account.tax'].search([('country_id', '=', record.country_id.id)], limit=1) and self.env['account.tax'].search([('country_id', '=', record.delivery_country_id.id)], limit=1):
                record.foreign_vat_header_mode = None
            elif self.env['account.tax.template'].search([('chart_template_id.country_id', '=', record.country_id.id)], limit=1) and self.env['account.tax.template'].search([('chart_template_id.country_id', '=', record.delivery_country_id.id)], limit=1):
                record.foreign_vat_header_mode = 'templates_found'
            else:
                record.foreign_vat_header_mode = 'no_template'

    def action_create_foreign_taxes(self):
        self.ensure_one()
        self.env['account.tax.template']._try_instantiating_foreign_taxes(self.country_id, self.company_id)
        self.env['account.tax.template']._try_instantiating_foreign_taxes(self.delivery_country_id, self.company_id)

    @api.constrains('country_id', 'country_group_id', 'delivery_country_id', 'state_ids', 'foreign_vat')
    def _validate_foreign_vat_country(self):
        for record in self:
            if record.foreign_vat:
                if record.country_id == record.company_id.account_fiscal_country_id:
                    if record.foreign_vat == record.company_id.vat:
                        raise ValidationError(_("You cannot create a fiscal position within your fiscal country with the same VAT number as the main one set on your company."))

                    if not record.state_ids:
                        if record.company_id.account_fiscal_country_id.state_ids:
                            raise ValidationError(_("You cannot create a fiscal position with a foreign VAT within your fiscal country without assigning it a state."))
                        else:
                            raise ValidationError(_("You cannot create a fiscal position with a foreign VAT within your fiscal country."))
                if record.country_group_id and record.delivery_country_id:
                    if record.delivery_country_id not in record.country_group_id.country_ids:
                        raise ValidationError(_("You cannot create a fiscal position with a country outside of the selected country group."))

                similar_fpos_domain = [
                    ('foreign_vat', '!=', False),
                    ('company_id', '=', record.company_id.id),
                    ('id', '!=', record.id),
                ]

                if record.country_group_id:
                    foreign_vat_country = self.country_group_id.country_ids.filtered(lambda c: c.code == record.foreign_vat[:2].upper())
                    if not foreign_vat_country:
                        raise ValidationError(_("The country code of the foreign VAT number does not match any country in the group."))
                    similar_fpos_domain += [('country_group_id', '=', record.country_group_id.id), ('country_id', '=', foreign_vat_country.id)]
                elif record.delivery_country_id:
                    similar_fpos_domain += [('delivery_country_id', '=', record.delivery_country_id.id), ('country_group_id', '=', False), ('country_id', '=', record.country_id.id)]

                if record.state_ids:
                    similar_fpos_domain.append(('state_ids', 'in', record.state_ids.ids))
                else:
                    similar_fpos_domain.append(('state_ids', '=', False))

                similar_fpos_count = self.env['account.fiscal.position'].search_count(similar_fpos_domain)
                if similar_fpos_count:
                    raise ValidationError(_("A fiscal position with a foreign VAT already exists in this region."))

    @api.onchange('country_id')
    def _onchange_country_id(self):
        return

    @api.onchange('delivery_country_id')
    def _onchange_delivery_country_id(self):
        if self.delivery_country_id:
            self.zip_from = self.zip_to = False
            self.state_ids = [(5,)]
            self.states_count = len(self.delivery_country_id.state_ids)

    @api.model
    def _get_fpos_by_region(self, country_id=False, state_id=False, zipcode=False, vat_required=False):
        if not country_id:
            return False
        base_domain = [
            ('auto_apply', '=', True),
            ('vat_required', '=', vat_required),
            ('company_id', 'in', [self.env.company.id, False]),
        ]
        null_state_dom = state_domain = [('state_ids', '=', False)]
        null_zip_dom = zip_domain = [('zip_from', '=', False), ('zip_to', '=', False)]
        null_country_dom = [('delivery_country_id', '=', False), ('country_group_id', '=', False)]

        if zipcode:
            zip_domain = [('zip_from', '<=', zipcode), ('zip_to', '>=', zipcode)]

        if state_id:
            state_domain = [('state_ids', '=', state_id)]

        domain_country = base_domain + [('delivery_country_id', '=', country_id)]
        domain_group = base_domain + [('country_group_id.country_ids', '=', country_id)]

        # Build domain to search records with exact matching criteria
        fpos = self.search(domain_country + state_domain + zip_domain, limit=1)
        # return records that fit the most the criteria, and fallback on less specific fiscal positions if any can be found
        if not fpos and state_id:
            fpos = self.search(domain_country + null_state_dom + zip_domain, limit=1)
        if not fpos and zipcode:
            fpos = self.search(domain_country + state_domain + null_zip_dom, limit=1)
        if not fpos and state_id and zipcode:
            fpos = self.search(domain_country + null_state_dom + null_zip_dom, limit=1)

        # fallback: country group with no state/zip range
        if not fpos:
            fpos = self.search(domain_group + null_state_dom + null_zip_dom, limit=1)

        if not fpos:
            # Fallback on catchall (no country, no group)
            fpos = self.search(base_domain + null_country_dom, limit=1)
        return fpos


class AccountFiscalPositionTax(models.Model):
    _inherit = 'account.fiscal.position.tax'

    tax_report_id = fields.Many2one('account.tax', string='Tax to Report')

    @api.onchange('tax_dest_id')
    def _onchange_tax_report_id(self):
        for record in self:
            if not record.tax_report_id and record.tax_dest_id and record.position_id.country_id == record.position_id.delivery_country_id:
                record.tax_report_id = record.tax_dest_id
