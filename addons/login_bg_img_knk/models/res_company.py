# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).


from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    bg_image = fields.Binary(string="Image")
