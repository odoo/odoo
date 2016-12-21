# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Addenda(models.Model):
    _name = 'edi.mx.addenda'

    name = fields.Char(
        string='Name',
        help='The name of the addenda to identify them.',
        required=True)

    body_xml = fields.Text(
        string='Body', 
        help='Body xml to render with qweb using the EDI values.')

