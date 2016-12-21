# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo import api
from odoo.addons.base.res.res_partner import FormatAddress

class FormatAddressExt(FormatAddress):

    @api.model
    def fields_view_get_address(self, arch):
        arch = super(FormatAddressExt, self).fields_view_get_address(arch)
        if self.env.user.company_id.country_id.enforce_cities:
            #render the partner address accordingly to address_view_id
            doc = etree.fromstring(arch)
            for address_node in doc.xpath("//field[@name='city']"):
                #do your stuff
                pass

                #Partner = self.env['res.partner'].with_context(no_address_format=True)
                #sub_view = Partner.fields_view_get(
                #    view_id=address_view_id.id, view_type='form', toolbar=False, submenu=False)
                #sub_view_node = etree.fromstring(sub_view['arch'])
                #address_node.getparent().replace(address_node, sub_view_node)
            arch = etree.tostring(doc)
        return arch
