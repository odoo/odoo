# Copyright Nova Code (http://www.novacode.nl)
# See LICENSE file for full licensing details.

from odoo import api, fields, models, _


class TranslationSource(models.Model):
    _name = 'formio.translation.source'
    _description = 'Formio Version Translation Source'
    _rec_name = 'source'

    property = fields.Text(string='Property', required=True)
    source = fields.Text(string='Source Term', required=True)
