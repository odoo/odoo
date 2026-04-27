# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class RealEstate(models.Model):
    """ Model to contain the information related to a real estate, when making an
    invoice linked to it. These data are useful for mod347 report's BOE export."""

    _name = 'l10n_es_reports.real.estate'
    _description = "Real Estate"

    name = fields.Char(string='Name', required=True, help="Name to display to identify this real estate.")
    invoice_ids = fields.One2many(string='Related Invoices', inverse_name='l10n_es_real_estate_id', comodel_name='account.move', required=True)

    cadastral_reference = fields.Selection(selection=[('1','Spanish Territory'),
                                                      ('2', 'Autonomous Community'),
                                                      ('3', 'No Cadastral Reference'),
                                                      ('4', 'Abroad')],
                                           string='Cadastral Reference',
                                           required=True,
                                           help="Cadastral reference: "
                                                "1. Spanish Territory:  Property with cadastral reference located in any point of the Spanish territory, except Basque Country and Navarre."
                                                "2. Autonomous Community: Property located in the Basque Country or Navarra."
                                                "3. Property in any of the above situations but without cadastral reference."
                                                "4. Property located abroad.")

    street_type = fields.Char(string='Street Type', size=5, required=True, help="Type of street, normalized according to INE.")
    street_name = fields.Char(string='Street Name', size=50, required=True, help="Name of the street where the building is located.")
    street_number_type = fields.Selection(string='Type of Street Number', selection=[('NUM', 'Number'), ('KM', 'Kilometer'), ('S/N', 'Without Number')], required=True, default='NUM', help="Type of the data contained in the street_number field.")
    street_number = fields.Integer(string="Street Number")
    street_number_km_qualifier = fields.Selection(string="Street Number Qualifier", selection=[('BIS', 'Bis'), ('MOD', 'Mod'), ('DUP', 'Dup'), ('ANT', 'Ant')], help="Qualifier for KM-typed street number")
    street_block = fields.Char(string='Block Number', size=3, help="Number of the building block in the street")
    portal = fields.Char(string='Portal', size=3)
    stairs = fields.Char(string='Stairs', size=3)
    floor = fields.Char(string='Floor Number', size=3)
    door = fields.Char(string='Door', size=3)
    address_complement = fields.Char(string="Address Complement", size=40, help="Any data necessary to complete the address")
    city = fields.Char(string="City", size=30, help="The city, if it is different from the municipality.")
    municipality = fields.Char(string="Municipality", size=30, required=True, help="Name of the Municipality")
    municipality_code = fields.Char(string="Municipality Code", size=5, required=True, help="Municipality code, as given by INE")
    province_code = fields.Char(string='Province Code', size=2, required=True)
    postal_code = fields.Char(string='Postal Code', size=5, required=True)
