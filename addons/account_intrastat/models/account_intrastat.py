# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountIntrastatCode(models.Model):
    _name = 'account.intrastat.code'
    _translate = False

    name = fields.Char(string='Intrastat Code')
    description = fields.Char(string='Description')


class AccountIntrastatRegion(models.Model):
    _name = 'account.intrastat.region'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    country_id = fields.Many2one('res.country', string='Country')
    description = fields.Char()

    _sql_constraints = [
        ('intrastat_region_code_unique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class AccountIntrastatTransaction(models.Model):
    _name = 'account.intrastat.transaction'
    _rec_name = 'code'

    code = fields.Char(required=True, readonly=True)
    description = fields.Text(readonly=True)

    _sql_constraints = [
        ('intrastat_transaction_code_unique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class AccountIntrastatTransport(models.Model):
    _name = 'account.intrastat.transport'

    code = fields.Char(required=True, readonly=True)
    name = fields.Char(string='Description', readonly=True)

    _sql_constraints = [
        ('intrastat_transaction_transport_unique', 'UNIQUE (code)', 'Code must be unique.'),
    ]
