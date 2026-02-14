# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TestUtmMailing(models.Model):
    _name = 'test.utm.mailing'
    _description = 'Fake Mailing to test UTMs'

    subject = fields.Char('Subject')
