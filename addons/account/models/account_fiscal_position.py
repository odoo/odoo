# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class AccountFiscalPosition(models.Model):
    _name = 'account.fiscal.position'
    _description = 'Fiscal Position'
    _order = 'sequence'

    sequence = fields.Integer()
    name = fields.Char(string='Fiscal Position', required=True)
    active = fields.Boolean(default=True,
        help="By unchecking the active field, you may hide a fiscal position without deleting it.")
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    account_ids = fields.One2many('account.fiscal.position.account', 'position_id', string='Account Mapping', copy=True)
    tax_ids = fields.One2many('account.fiscal.position.tax', 'position_id', string='Tax Mapping', copy=True)
    note = fields.Text('Notes', translate=True, help="Legal mentions that have to be printed on the invoices.")
    auto_apply = fields.Boolean(string='Detect Automatically', help="Apply automatically this fiscal position.")
    vat_required = fields.Boolean(string='VAT required', help="Apply only if partner has a VAT number.")
    company_country_id = fields.Many2one(string="Company Country", related='company_id.country_id')
    country_id = fields.Many2one('res.country', string='Country',
        help="Apply only if delivery country matches.")
    country_group_id = fields.Many2one('res.country.group', string='Country Group',
        help="Apply only if delivery country matches the group.")
    state_ids = fields.Many2many('res.country.state', string='Federal States')
    zip_from = fields.Char(string='Zip Range From')
    zip_to = fields.Char(string='Zip Range To')
    # To be used in hiding the 'Federal States' field('attrs' in view side) when selected 'Country' has 0 states.
    states_count = fields.Integer(compute='_compute_states_count')
    foreign_vat = fields.Char(string="Foreign Tax ID", help="The tax ID of your company in the region mapped by this fiscal position.")

    def _compute_states_count(self):
        for position in self:
            position.states_count = len(position.country_id.state_ids)

    @api.constrains('zip_from', 'zip_to')
    def _check_zip(self):
        for position in self:
            if position.zip_from and position.zip_to and position.zip_from > position.zip_to:
                raise ValidationError(_('Invalid "Zip Range", please configure it properly.'))

    @api.constrains('country_id', 'state_ids', 'foreign_vat')
    def _validate_foreign_vat_country(self):
        for record in self:
            if record.foreign_vat and record.country_id == record.company_id.account_fiscal_country_id:
                if record.foreign_vat == record.company_id.vat:
                    raise ValidationError(_("You cannot create a fiscal position within your fiscal country with the same VAT number as the main one set on your company."))

                if not record.state_ids:
                    if record.company_id.account_fiscal_country_id.state_ids:
                        raise ValidationError(_("You cannot create a fiscal position with a foreign VAT within your fiscal country without assigning it a state."))
                    else:
                        raise ValidationError(_("You cannot create a fiscal position with a foreign VAT within your fiscal country."))

    def map_tax(self, taxes, product=None, partner=None):
        if not self:
            return taxes
        result = self.env['account.tax']
        for tax in taxes:
            taxes_correspondance = self.tax_ids.filtered(lambda t: t.tax_src_id == tax)
            result |= taxes_correspondance.tax_dest_id if taxes_correspondance else tax
        return result

    def map_account(self, account):
        for pos in self.account_ids:
            if pos.account_src_id == account:
                return pos.account_dest_id
        return account

    def map_accounts(self, accounts):
        """ Receive a dictionary having accounts in values and try to replace those accounts accordingly to the fiscal position.
        """
        ref_dict = {}
        for line in self.account_ids:
            ref_dict[line.account_src_id] = line.account_dest_id
        for key, acc in accounts.items():
            if acc in ref_dict:
                accounts[key] = ref_dict[acc]
        return accounts

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id:
            self.zip_from = self.zip_to = self.country_group_id = False
            self.state_ids = [(5,)]
            self.states_count = len(self.country_id.state_ids)

    @api.onchange('country_group_id')
    def _onchange_country_group_id(self):
        if self.country_group_id:
            self.zip_from = self.zip_to = self.country_id = False
            self.state_ids = [(5,)]

    @api.model
    def _convert_zip_values(self, zip_from='', zip_to=''):
        max_length = max(len(zip_from), len(zip_to))
        if zip_from.isdigit():
            zip_from = zip_from.rjust(max_length, '0')
        if zip_to.isdigit():
            zip_to = zip_to.rjust(max_length, '0')
        return zip_from, zip_to

    @api.model
    def create(self, vals):
        zip_from = vals.get('zip_from')
        zip_to = vals.get('zip_to')
        if zip_from and zip_to:
            vals['zip_from'], vals['zip_to'] = self._convert_zip_values(zip_from, zip_to)
        return super(AccountFiscalPosition, self).create(vals)

    def write(self, vals):
        zip_from = vals.get('zip_from')
        zip_to = vals.get('zip_to')
        if zip_from or zip_to:
            for rec in self:
                vals['zip_from'], vals['zip_to'] = self._convert_zip_values(zip_from or rec.zip_from, zip_to or rec.zip_to)
        return super(AccountFiscalPosition, self).write(vals)

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
        null_country_dom = [('country_id', '=', False), ('country_group_id', '=', False)]

        if zipcode:
            zip_domain = [('zip_from', '<=', zipcode), ('zip_to', '>=', zipcode)]

        if state_id:
            state_domain = [('state_ids', '=', state_id)]

        domain_country = base_domain + [('country_id', '=', country_id)]
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

    @api.model
    def get_fiscal_position(self, partner_id, delivery_id=None):
        """
        :return: fiscal position found (recordset)
        :rtype: :class:`account.fiscal.position`
        """
        if not partner_id:
            return self.env['account.fiscal.position']

        # This can be easily overridden to apply more complex fiscal rules
        PartnerObj = self.env['res.partner']
        partner = PartnerObj.browse(partner_id)

        # if no delivery use invoicing
        if delivery_id:
            delivery = PartnerObj.browse(delivery_id)
        else:
            delivery = partner

        # partner manually set fiscal position always win
        if delivery.property_account_position_id or partner.property_account_position_id:
            return delivery.property_account_position_id or partner.property_account_position_id

        # First search only matching VAT positions
        vat_required = bool(partner.vat)
        fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, vat_required)

        # Then if VAT required found no match, try positions that do not require it
        if not fp and vat_required:
            fp = self._get_fpos_by_region(delivery.country_id.id, delivery.state_id.id, delivery.zip, False)

        return fp or self.env['account.fiscal.position']


class AccountFiscalPositionTax(models.Model):
    _name = 'account.fiscal.position.tax'
    _description = 'Tax Mapping of Fiscal Position'
    _rec_name = 'position_id'
    _check_company_auto = True

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='position_id.company_id', store=True)
    tax_src_id = fields.Many2one('account.tax', string='Tax on Product', required=True, check_company=True)
    tax_dest_id = fields.Many2one('account.tax', string='Tax to Apply', check_company=True)

    _sql_constraints = [
        ('tax_src_dest_uniq',
         'unique (position_id,tax_src_id,tax_dest_id)',
         'A tax fiscal position could be defined only one time on same taxes.')
    ]


class AccountFiscalPositionAccount(models.Model):
    _name = 'account.fiscal.position.account'
    _description = 'Accounts Mapping of Fiscal Position'
    _rec_name = 'position_id'
    _check_company_auto = True

    position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
        required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', related='position_id.company_id', store=True)
    account_src_id = fields.Many2one('account.account', string='Account on Product',
        check_company=True, required=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    account_dest_id = fields.Many2one('account.account', string='Account to Use Instead',
        check_company=True, required=True,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")

    _sql_constraints = [
        ('account_src_dest_uniq',
         'unique (position_id,account_src_id,account_dest_id)',
         'An account fiscal position could be defined only one time on same accounts.')
    ]
