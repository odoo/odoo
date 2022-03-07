# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import api, fields, models, tools, _

# Global variables used for the warning fields declared on the res.partner
# in the following modules : sale, purchase, account, stock

ADDRESS_FIELDS = ('street', 'street2', 'zip', 'city', 'state_id', 'country_id')


class AddressMixin(models.AbstractModel):
    _name = "address.mixin"
    _description = 'Address Format'

    vat = fields.Char(string='Tax ID', index=True, help="The Tax Identification Number. Complete it if the contact is subjected to government taxes. Used in some legal statements.")
    street = fields.Char(compute='_compute_street', inverse='_inverse_street', store=True)
    street2 = fields.Char(compute='_compute_street2', inverse='_inverse_street2', store=True)
    zip = fields.Char(change_default=True, compute='_compute_zip', inverse='_inverse_zip', store=True)
    city = fields.Char(compute='_compute_city', inverse='_inverse_city', store=True)
    city_id = fields.Many2one(comodel_name='res.city', string='City ID')
    country_enforce_cities = fields.Boolean(related='country_id.enforce_cities')
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]", compute='_compute_state_id',
                               inverse='_inverse_state_id', store=True)

    contact_address = fields.Char(compute='_compute_contact_address', string='Complete Address')
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    country_code = fields.Char(related='country_id.code', string="Country Code")
    latitude = fields.Float(string='Geo Latitude', digits=(10, 7))
    longitude = fields.Float(string='Geo Longitude', digits=(10, 7))

    def _get_street_split(self):
        self.ensure_one()
        return tools.street_split(self.street or '')

        # hooks for overriding address fields other modules

    def _compute_street(self):
        pass

    def _inverse_street(self):
        pass

    def _compute_street2(self):
        pass

    def _inverse_street2(self):
        pass

    @api.depends("city_id", "country_enforce_cities")
    def _compute_city(self):
        for partner in self.filtered(lambda rec: rec.country_enforce_cities):
            partner.city = self.city_id.name or ''

    def _inverse_city(self):
        pass

    @api.depends("city_id", "country_enforce_cities")
    def _compute_state_id(self):
        for partner in self.filtered(lambda rec: rec.country_enforce_cities and rec.city_id):
            partner.state_id = self.city_id.state_id

    def _inverse_state_id(self):
        for partner in self.filtered(lambda rec: rec.country_enforce_cities):
            if partner.city_id.state_id != partner.state_id:
                partner.city_id = False

    @api.depends("city_id", "country_enforce_cities")
    def _compute_zip(self):
        for partner in self.filtered(lambda rec: rec.country_enforce_cities and rec.city_id):
            partner.city = self.city_id.zipcode

    def _inverse_zip(self):
        # should be optimized obviously
        City = self.env["res.city"]
        for partner in self.filtered(lambda rec: rec.country_enforce_cities):
            city = City.search([('state_id', '=', partner.state_id), ('zip', '=', partner.zip)])
            if city:
                partner.city_id = city


    @api.depends(lambda self: self._display_address_depends())
    def _compute_contact_address(self):
        for partner in self:
            partner.contact_address = partner._display_address()

    @api.model
    def _fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if (not view_id) and (view_type == 'form') and self._context.get('force_email'):
            view_id = self.env.ref('base.view_partner_simple_form').id
        res = super()._fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                    submenu=submenu)
        if view_type == 'form':
            res['arch'] = self._fields_view_get_address(res['arch'])
        return res
    def _fields_view_get_address(self, arch):
        # consider the country of the user, not the country of the partner we want to display
        address_view_id = self.env.company.country_id.address_view_id.sudo()
        if address_view_id and not self._context.get('no_address_format') and (not address_view_id.model or address_view_id.model == self._name):
            #render the partner address accordingly to address_view_id
            doc = etree.fromstring(arch)
            for address_node in doc.xpath("//div[hasclass('o_address_format')]"):
                Partner = self.env['res.partner'].with_context(no_address_format=True)
                sub_view = Partner.fields_view_get(
                    view_id=address_view_id.id, view_type='form', toolbar=False, submenu=False)
                sub_view_node = etree.fromstring(sub_view['arch'])
                # if the model is different than res.partner, there are chances that the view won't work
                # (e.g fields not present on the model). In that case we just return arch
                if self._name != 'res.partner':
                    try:
                        self.env['ir.ui.view'].postprocess_and_fields(sub_view_node, model=self._name)
                    except ValueError:
                        return arch
                address_node.getparent().replace(address_node, sub_view_node)
            arch = etree.tostring(doc, encoding='unicode')
        return arch

    @api.onchange('country_id')
    def _onchange_country_id(self):
        if self.country_id and self.country_id != self.state_id.country_id:
            self.state_id = False

    @api.onchange('state_id')
    def _onchange_state(self):
        if self.state_id.country_id:
            self.country_id = self.state_id.country_id

    @api.model
    def _address_fields(self):
        """Returns the list of address fields that are synced from the parent."""
        return list(ADDRESS_FIELDS)

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return self._address_fields()

    def update_address(self, vals):
        addr_vals = {key: vals[key] for key in self._address_fields() if key in vals}
        if addr_vals:
            return super().write(addr_vals)

    def _fields_sync(self, values):
        pass


    @api.model
    def _get_default_address_format(self):
        return "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"

    @api.model
    def _get_address_format(self):
        return self.country_id.address_format or self._get_default_address_format()

    def _prepare_display_address(self, without_company=False):
        # get the information that will be injected into the display format
        # get the address format
        address_format = self._get_address_format()
        args = {
            'state_code': self.state_id.code or '',
            'state_name': self.state_id.name or '',
            'country_code': self.country_id.code or '',
            'country_name': self._get_country_name(),
            # 'company_name': self.commercial_company_name or '',
        }
        for field in self._formatting_address_fields():
            args[field] = getattr(self, field) or ''
        if without_company:
            args['company_name'] = ''
        # elif self.commercial_company_name:
        #     address_format = '%(company_name)s\n' + address_format
        return address_format, args

    def _display_address(self, without_company=False):
        '''
        The purpose of this function is to build and return an address formatted accordingly to the
        standards of the country where it belongs.

        :param without_company: if address contains company
        :returns: the address formatted in a display that fit its country habits (or the default ones
            if not country is specified)
        :rtype: string
        '''
        address_format, args = self._prepare_display_address(without_company)
        return address_format % args

    def _display_address_depends(self):
        # field dependencies of method _display_address()
        return self._formatting_address_fields() + [
            'country_id', 'company_name', 'state_id',
        ]

    def _get_country_name(self):
        return self.country_id.name or ''
