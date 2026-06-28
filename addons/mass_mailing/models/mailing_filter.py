# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class MailingFilter(models.Model):
    """ This model stores mass mailing or marketing campaign domain as dynamic
    lists (quite similar to 'ir.filters' but dedicated to mailing apps).
    Frequently used domains can be reused easily."""
    _name = 'mailing.filter'
    _description = 'Mailing Dynamic List'
    _order = 'create_date DESC'

    # override create_uid field to display default value while creating filter from 'Configuration' menus
    create_uid = fields.Many2one('res.users', 'Saved by', index=True, readonly=True, default=lambda self: self.env.user)
    name = fields.Char(string='List Name', required=True)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color', default=0)
    mailing_domain = fields.Char(string='Filter Domain', required=True, default="[]")
    mailing_model_id = fields.Many2one('ir.model', string='Recipients Model', required=True, ondelete='cascade', domain=[('is_mailing_enabled', '=', True)])
    mailing_model_name = fields.Char(string='Recipients Model Name', related='mailing_model_id.model')
    mailing_count = fields.Integer('Number of Mailing', compute='_compute_mailing_count')

    @api.constrains('mailing_domain', 'mailing_model_id')
    def _check_mailing_domain(self):
        """ Check that if the mailing domain is set, it is a valid one """
        for mailing_filter in self:
            if mailing_filter.mailing_domain != "[]":
                try:
                    self.env[mailing_filter.mailing_model_id.model].search_count(literal_eval(mailing_filter.mailing_domain))
                except:
                    raise ValidationError(
                        _("The filter domain is not valid for this recipients.")
                    )

    # ------------------------------------------------------
    # COMPUTE
    # ------------------------------------------------------

    def _compute_mailing_count(self):
        groups = dict(
            self.env['mailing.mailing']._read_group(
            domain=[('mailing_filter_ids', 'in', self.ids)],
            groupby=['mailing_filter_ids'],
            aggregates=['__count']))
        for mailing_filter in self:
            mailing_filter.mailing_count = groups.get(mailing_filter, 0)

    # ------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------

    def action_view_recipients(self):
        """Redirect to the list view of the model of the selected dynamic
        list, with the domain of the latter set as the domain of that view.
        If the model is `mailing.contact`, the `New`, `Paste` and `Upload`
        buttons will be hidden."""
        self.ensure_one()
        if self.mailing_model_name == 'mailing.contact':
            views = [(self.env.ref('mass_mailing.mailing_contact_view_list_from_filter').id, 'list'), (False, 'form')]
        else:
            views = [(False, 'list'), (False, 'form')]

        return {
            'type': 'ir.actions.act_window',
            'name': self.mailing_model_id.name,
            'res_model': self.mailing_model_name,
            'views': views,
            'target': 'current',
            'domain': literal_eval(self.mailing_domain),
            'context': {'create': False},
            'help': self.env._("""
                <p class="o_view_nocontent_smiling_face">No record currently matches your rules!</p>
            """),
        }

    def action_view_mailings(self):
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.mailing_mailing_action_mail')
        action['domain'] = [('mailing_filter_ids', 'in', self.ids)]
        return action

    def action_send_mailing(self):
        """Open the mailing form view, with the current model & domain set as the mailing model & mailing domain.
        respectively"""
        if not self.mailing_model_id.is_mailing_enabled:
            raise UserError(_("Cannot use the model %s to send a mailing. Only mailing models can be used.", self.mailing_model_id.name))
        action = self.env["ir.actions.actions"]._for_xml_id('mass_mailing.mailing_mailing_action_mail')
        action.update({
            'context': {
                'default_mailing_filter_ids': self.ids,
                'default_mailing_model_id': self.mailing_model_id.id},
            'views': [(False, 'form')]
        })
        return action

    def action_duplicate(self):
        self.ensure_one()
        if self.copy():
            return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
        return False
