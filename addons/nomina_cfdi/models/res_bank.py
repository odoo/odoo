# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Bank(models.Model):
    _inherit = "res.bank"

    c_banco = fields.Char(string='Clave de Banco')