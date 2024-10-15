# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import portal, mail


class ResConfigSettings(mail.ResConfigSettings, portal.ResConfigSettings):

    digest_emails = fields.Boolean(string="Digest Emails", config_parameter='digest.default_digest_emails')
    digest_id = fields.Many2one('digest.digest', string='Digest Email', config_parameter='digest.default_digest_id')
