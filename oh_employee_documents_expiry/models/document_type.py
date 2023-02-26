# -*- coding: utf-8 -*-
from datetime import datetime, date, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import Warning


class DocumentType(models.Model):
    _name = 'document.type'

    name = fields.Char(string="Name", required=True, help="Name")
