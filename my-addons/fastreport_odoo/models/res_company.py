# -*- coding: utf-8 -*-

from odoo import models, fields

class ResCompany(models.Model):

    _inherit = 'res.company'

    fastreport_server_url = fields.Char(help="FastReport Server Url.")

    reports_save_path = fields.Char(help="FastReport Storeage Path.")
