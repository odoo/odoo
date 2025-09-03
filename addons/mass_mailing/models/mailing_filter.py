# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MailingFilter(models.Model):
    """ This model stores mass mailing or marketing campaign domain as filters
    (quite similar to 'ir.filters' but dedicated to mailing apps). Frequently
    used domains can be reused easily. """
    _name = 'mailing.filter'
    _description = 'Mailing Favorite Filters'
    _order = 'create_date DESC'

    # override create_uid field to display default value while creating filter from 'Configuration' menus
    create_uid = fields.Many2one('res.users', 'Saved by', index=True, readonly=True, default=lambda self: self.env.user)
    name = fields.Char(string='Filter Name', required=True)
    mailing_domain = fields.Char(string='Filter Domain', required=True)
    mailing_model_id = fields.Many2one('ir.model', string='Recipients Model', required=True, ondelete='cascade')
    mailing_model_name = fields.Char(string='Recipients Model Name', related='mailing_model_id.model')

    @api.constrains('mailing_domain', 'mailing_model_id')
    def _check_mailing_domain(self):
        """ Check that if the mailing domain is set, it is a valid one """
        for mailing_filter in self:
            if mailing_filter.mailing_domain != "[]":
                try:
                    self.env[mailing_filter.mailing_model_id.model].search_count(literal_eval(mailing_filter.mailing_domain))
                except Exception:  # noqa: BLE001
                    raise ValidationError(
                        _("The filter domain is not valid for this recipients.")
                    )
