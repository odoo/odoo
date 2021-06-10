# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Criterias(models.Model):
    _name = 'tecdoc.criterias'
    _description = 'Description of all criteria'

    krit_nr = fields.Integer("Criterion Number", required=True)
    name = fields.Char("Description Number")
    typ = fields.Selection([('A', 'Alphanumerical'),
                            ('N', 'Numerical'),
                            ('D', "Date"),
                            ('K', "Key"),
                            ('V', "without value")],
                           "Criterion Type", default='V')
    max_len = fields.Integer("Maximum length")
    ok_artikel = fields.Boolean("article")
    tab_nr = fields.Integer("N° for type ‘K’ table")
    ok_nkw = fields.Boolean("CV linkages")
    ok_pkw = fields.Boolean("PC linkages")
    ok_motor = fields.Boolean("Engine linkages")
    ok_fahrerhaus = fields.Boolean("Driver Cab linkages")
    stucklisten_criterion = fields.Boolean("Parts List criterion")
    zubehor_criterion = fields.Boolean("Accessory List criterion")
    mehrfach_verwendung = fields.Boolean("more than once within a linkage")
    abk = fields.Char("Abbreviation")
    einheit = fields.Char("Unit")
    intervall_criterion = fields.Boolean("is an interval criterion")
    nachfolge_criterion = fields.Boolean("is successor to...")


class KeyTables(models.Model):
    _name = 'tecdoc.tables'
    _description = 'Table definition'

    tab_nr = fields.Integer("Key Table Number")
    name = fields.Char("Key Table Name", required=True)
    tab_typ = fields.Selection([('A', "Alphanumerical"),('N', 'Numerical')],
                               "Type denifition",
                               default="A")
    key_entries_id = fields.One2many('tecdoc.tables.entries',
                                     'key_table_id',
                                     string="Key Table Entries")


class KeyTablesEntries(models.Model):
    _name = 'tecdoc.tables.entries'
    _description = 'Key Table Entries'

    tab_nr = fields.Integer("Key Table Number")
    name = fields.Char("Key Entry Name")
    key = fields.Char("Key table entry")
    sort_nr = fields.Integer("Sort Key")
    key_table_id = fields.Many2one('tecdoc.tables')
