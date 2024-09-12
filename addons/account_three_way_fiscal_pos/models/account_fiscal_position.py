from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    fiscal_country_id = fields.Many2one('res.country', string='Fiscal Country',
        help="Country from which's taxes are available for the fiscal position mapping.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals = self.adjust_vals_fiscal_country_id(vals)
            vals = self.adjust_vals_country_id(vals)
            zip_from = vals.get('zip_from')
            zip_to = vals.get('zip_to')
            if zip_from and zip_to:
                vals['zip_from'], vals['zip_to'] = self._convert_zip_values(zip_from, zip_to)
        return super().create(vals_list)

    def write(self, vals):
        vals = self.adjust_vals_fiscal_country_id(vals)
        vals = self.adjust_vals_country_id(vals)
        zip_from = vals.get('zip_from')
        zip_to = vals.get('zip_to')
        if zip_from or zip_to:
            for rec in self:
                vals['zip_from'], vals['zip_to'] = self._convert_zip_values(zip_from or rec.zip_from, zip_to or rec.zip_to)
        return super().write(vals)

    def adjust_vals_fiscal_country_id(self, vals):
        foreign_vat = vals.get('foreign_vat')
        country_id = self.country_id or vals.get('country_id')
        if not (self.fiscal_country_id or vals.get("fiscal_country_id")):
            if country_id:
                vals['fiscal_country_id'] = country_id
            elif foreign_vat:
                vals['fiscal_country_id'] = self.env['res.country'].search([("code", "=", foreign_vat[:2].upper())], limit=1) or False
        return vals

    def adjust_vals_country_id(self, vals):
        fiscal_country_id = self.fiscal_country_id or vals.get('fiscal_country_id')
        country_id = self.country_id or vals.get('country_id')
        if not country_id and fiscal_country_id:
            vals['country_id'] = fiscal_country_id
        return vals

    @api.depends('foreign_vat', 'country_id')
    def _compute_foreign_vat_header_mode(self):
        for record in self:
            if not record.foreign_vat or not record.country_id:
                record.foreign_vat_header_mode = None
                continue

            if self.env['account.tax'].search([('country_id', '=', record.country_id.id)], limit=1) and self.env['account.tax'].search([('country_id', '=', record.fiscal_country_id.id)], limit=1):
                record.foreign_vat_header_mode = None
            elif self.env['account.tax.template'].search([('chart_template_id.country_id', '=', record.country_id.id)], limit=1) or self.env['account.tax.template'].search([('chart_template_id.country_id', '=', record.fiscal_country_id.id)], limit=1):
                record.foreign_vat_header_mode = 'templates_found'
            else:
                record.foreign_vat_header_mode = 'no_template'

    @api.constrains('fiscal_country_id', 'country_id', 'country_group_id', 'state_ids', 'foreign_vat')
    def _validate_foreign_vat_country(self):
        for record in self:
            if record.foreign_vat:
                if record.fiscal_country_id == record.company_id.account_fiscal_country_id:
                    if record.foreign_vat == record.company_id.vat:
                        raise ValidationError(_("You cannot create a fiscal position within your fiscal country with the same VAT number as the main one set on your company."))

                    if not record.state_ids:
                        if record.company_id.account_fiscal_country_id.state_ids:
                            raise ValidationError(_("You cannot create a fiscal position with a foreign VAT within your fiscal country without assigning it a state."))
                        else:
                            raise ValidationError(_("You cannot create a fiscal position with a foreign VAT within your fiscal country."))
                if record.country_group_id and record.country_id:
                    if record.country_id not in record.country_group_id.country_ids:
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
                    similar_fpos_domain += [('country_group_id', '=', record.country_group_id.id), ('fiscal_country_id', '=', foreign_vat_country.id)]
                elif record.country_id:
                    similar_fpos_domain += [('country_id', '=', record.country_id.id), ('country_group_id', '=', False), ('fiscal_country_id', '=', record.fiscal_country_id.id)]

                if record.state_ids:
                    similar_fpos_domain.append(('state_ids', 'in', record.state_ids.ids))
                else:
                    similar_fpos_domain.append(('state_ids', '=', False))
                similar_fpos_count = self.env['account.fiscal.position'].search_count(similar_fpos_domain)
                if similar_fpos_count:
                    raise ValidationError(_("A fiscal position with a foreign VAT already exists in this region."))

    def action_create_foreign_taxes(self):
        super().action_create_foreign_taxes()
        self.env['account.tax.template']._try_instantiating_foreign_taxes(self.fiscal_country_id, self.company_id)

    def _get_fiscal_country(self):
        return self.fiscal_country_id
