# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import api, models, fields
from odoo.tools.translate import _


class Partner(models.Model):
    _inherit = 'res.partner'

    country_enforce_cities = fields.Boolean(related='country_id.enforce_cities', readonly=True)
    city_id = fields.Many2one('res.city', string='City')

    @api.onchange('city_id')
    def _onchange_city_id(self):
        self.city = self.city_id.name
        self.zip = self.city_id.zipcode
        self.state_id = self.city_id.state_id

    @api.model
    def _fields_view_get_address(self, arch):
        arch = super(Partner, self)._fields_view_get_address(arch)
        # render the partner address accordingly to address_view_id
        doc = etree.fromstring(arch)
        if doc.xpath("//field[@name='city_id']"):
           return arch
        for city_node in doc.xpath("//field[@name='city']"):
            replacement_xml = """
            <div>
                <field name="country_enforce_cities" invisible="1"/>
                <field name='city' placeholder="%s" attrs="{'invisible': [('country_enforce_cities', '=', True), ('city_id', '!=', False)], 'readonly': [('type', '=', 'contact'), ('parent_id', '!=', False)]}"/>
                <field name='city_id' placeholder="%s" attrs="{'invisible': [('country_enforce_cities', '=', False)], 'readonly': [('type', '=', 'contact'), ('parent_id', '!=', False)]}" context="{'default_country_id': country_id}" domain="[('country_id', '=', country_id)]"/>
            </div>
            """ % (_('City'), _('City'))
            city_id_node = etree.fromstring(replacement_xml)
            city_node.getparent().replace(city_node, city_id_node)

        arch = etree.tostring(doc, encoding='unicode')
        return arch
