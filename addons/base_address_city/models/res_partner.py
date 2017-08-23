# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import api, models, fields

class Partner(models.Model):
    _inherit = 'res.partner'

    country_enforce_cities = fields.Boolean(related='country_id.enforce_cities')
    city_id = fields.Many2one('res.city', string='Company')

    @api.onchange('city_id')
    def _onchange_city_id(self):
        self.city = self.city_id.name
        self.zip = self.city_id.zipcode
        self.state_id = self.city_id.state_id

    @api.model
    def _fields_view_get_address(self, arch):
        arch = super(Partner, self)._fields_view_get_address(arch)
        if not self._context.get('no_address_format'):
            return arch
        # render the partner address accordingly to address_view_id
        doc = etree.fromstring(arch)
        for city_node in doc.xpath("//field[@name='city']"):
            view = self.env.ref(
                'base_address_city.view_partner_city_address_form')
            arch = view._read_template(view.id)
            replacement_xml = etree.tostring(
                etree.fromstring(arch).xpath("//div")[0])
            city_id_node = etree.fromstring(replacement_xml)
            city_node.getparent().replace(city_node, city_id_node)

        arch = etree.tostring(doc)
        return arch
