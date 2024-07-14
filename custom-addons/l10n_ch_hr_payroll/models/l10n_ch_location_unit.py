# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class L10nChWorkLocation(models.Model):
    _name = 'l10n.ch.location.unit'
    _description = 'Work Place - Swiss Payroll'
    _rec_name = 'partner_id'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string="Working Address", required=True)
    bur_ree_number = fields.Char(
        string="BUR-REE-Number",
        required=True,
        help="Depending on the structure of the company and the number of workplaces, there are one or more REE numbers.")
    canton = fields.Selection([
        ('AG', 'Argovie'),
        ('AI', 'Appenzell Rhodes-Intérieures'),
        ('AR', 'Appenzell Rhodes-Extérieures'),
        ('BE', 'Berne'),
        ('BL', 'Bâle-Campagne'),
        ('BS', 'Bâle-Ville'),
        ('FR', 'Fribourg'),
        ('GE', 'Genève'),
        ('GL', 'Glaris'),
        ('GR', 'Grisons'),
        ('JU', 'Jura'),
        ('LU', 'Lucerne'),
        ('NE', 'Neuchâtel'),
        ('NW', 'Nidwald'),
        ('OW', 'Obwald'),
        ('SG', 'Saint-Gall'),
        ('SH', 'Schaffhouse'),
        ('SO', 'Soleure'),
        ('SZ', 'Schwytz'),
        ('TG', 'Thurgovie'),
        ('TI', 'Tessin'),
        ('UR', 'Uri'),
        ('VD', 'Vaud'),
        ('VS', 'Valais'),
        ('ZG', 'Zoug'),
        ('ZH', 'Zurich'),
    ], required=True)
    dpi_number = fields.Char('DPI Number', required=True)  # Equivalent to SSL nummer
    municipality = fields.Char(string="Municipality ID", required=True)

    _sql_constraints = [
        ('_unique', 'unique (company_id, partner_id)', "A work location cannot be set more than once for the same company and partner."),
    ]
