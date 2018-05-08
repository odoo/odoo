# -*- coding: utf-8 -*-

from odoo import fields, models


class AccountIntrastatCode(models.Model):
    '''
    Commodity codes used for statistical purposes that are provided by the European Union for the statistics on
    International Trade in Goods in all EU countries.

    In Odoo, these codes can be set on invoice lines.

    The list of codes is available on:
    https://www.cbs.nl/en-gb/deelnemers%20enquetes/overzicht/bedrijven/onderzoek/lopend/international-trade-in-goods/idep-code-lists
    '''
    _name = 'account.intrastat.code'
    _translate = False

    name = fields.Char(string='Intrastat Code')
    description = fields.Char(string='Description')


class AccountIntrastatRegion(models.Model):
    '''
    Sub-part of a country.
    '''
    _name = 'account.intrastat.region'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    country_id = fields.Many2one('res.country', string='Country')
    description = fields.Char()

    _sql_constraints = [
        ('intrastat_region_code_unique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class AccountIntrastatTransaction(models.Model):
    '''
    A transaction is a movement of goods in the intrastat point of view.

    - Goods could be obtained entirely within the EU.
    - Goods from countries outside the EU that are put into free circulation in the EU.
    - Goods that are a combination of the above.
    '''
    _name = 'account.intrastat.transaction'
    _rec_name = 'code'

    code = fields.Char(required=True, readonly=True)
    description = fields.Text(readonly=True)

    _sql_constraints = [
        ('intrastat_transaction_code_unique', 'UNIQUE (code)', 'Code must be unique.'),
    ]


class AccountIntrastatTransport(models.Model):
    '''
    The mode of transport is defined according to the active vehicle that moves the goods across the border.
    '''
    _name = 'account.intrastat.transport'

    code = fields.Char(required=True, readonly=True)
    name = fields.Char(string='Description', readonly=True)

    _sql_constraints = [
        ('intrastat_transaction_transport_unique', 'UNIQUE (code)', 'Code must be unique.'),
    ]
