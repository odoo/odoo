# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons import website_partner, website, website_crm_partner_assign


class ResPartner(website_crm_partner_assign.ResPartner, website_partner.ResPartner):


    website_tag_ids = fields.Many2many(
        'res.partner.tag',
        'res_partner_res_partner_tag_rel',
        'partner_id',
        'tag_id',
        string='Website tags',
        help="Filter published customers on the .../customers website page",
    )

    def get_backend_menu_id(self):
        return self.env.ref('contacts.menu_contacts').id


class ResPartnerTag(models.Model, website.WebsitePublishedMixin):

    _description = 'Partner Tags - These tags can be used on website to find customers by sector, or ...'

    @api.model
    def get_selection_class(self):
        classname = ['info', 'primary', 'success', 'warning', 'danger']
        return [(x, str.title(x)) for x in classname]

    name = fields.Char('Category Name', required=True, translate=True)
    partner_ids = fields.Many2many('res.partner', 'res_partner_res_partner_tag_rel', 'tag_id', 'partner_id', string='Partners')
    classname = fields.Selection('get_selection_class', 'Class', default='info', help="Bootstrap class to customize the color", required=True)
    active = fields.Boolean('Active', default=True)

    def _default_is_published(self):
        return True
