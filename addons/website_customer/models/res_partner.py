# -*- coding: utf-8 -*-

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    website_tag_ids = fields.Many2many('res.partner.tag', 'res_partner_res_partner_tag_rel', 'partner_id', 'tag_id', string='Website tags', oldname="tag_ids")


class ResPartnerTag(models.Model):
    _description = 'Partner Tags - These tags can be used on website to find customers by sector, or ... '
    _name = 'res.partner.tag'
    _inherit = 'website.published.mixin'

    name = fields.Char('Category Name', required=True, translate=True)
    partner_ids = fields.Many2many('res.partner', 'res_partner_res_partner_tag_rel', 'tag_id', 'partner_id', string='Partners')
    classname = fields.Selection(selection='get_selection_class', string="Class", default='default', required=True, help="Bootstrap class to customize the color")
    website_published = fields.Boolean(default=True)
    active = fields.Boolean('Active', default=True)

    def get_selection_class(self):
        classname = ['default', 'primary', 'success', 'warning', 'danger']
        return [(x, str.title(x)) for x in classname]

