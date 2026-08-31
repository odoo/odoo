# -*- coding: utf-8 -*-
"""Phase 5 — Bundle paperwork, traffic emails, and Order Confirmation pass-through.

Replaces SF's Conga Composer + Gmail templates with Odoo `mail.template` + QWeb
report variants. Each bundle Program has its own paperwork-email recipients;
those are looked up on `mv.programs` (new fields added here).

SF Workflow refs: 12 (Bundles), 29 (Order Confirmations).
"""
import logging
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MvProgramsPhase5(models.Model):
    _name = 'mv.programs'
    _inherit = ['mv.programs']

    # Per-bundle routing fields (SF Workflow 12 variants)
    is_bundle = fields.Boolean(
        string='Bundle Program',
        help='Tick on the Program record if this network operates as a Bundle (American Spirit Connect, Gray Bundles, Tegna Connect, Hearst Unwired, Univision Connect, etc.).',
    )
    bundle_paperwork_to = fields.Char(
        string='Paperwork Recipients (TO)',
        help='Comma-separated emails that receive the bundle paperwork when "Send Bundle Paperwork" is clicked.',
    )
    bundle_paperwork_cc = fields.Char(
        string='Paperwork Recipients (CC)',
    )
    traffic_email = fields.Char(
        string='Traffic Email',
        help='Email address for sending traffic instructions (cannot include rates).',
    )
    bundle_capacity_30 = fields.Integer(
        string='Bundle Capacity (Equiv :30)',
        help='Static capacity in Equiv :30 units per week (AS=70, Bounce Gray=200, Primary Gray=125, Retro Gray=250, Telemundo Gray=35, Primary Tegna=80, Tegna Connect One=150, Hearst=80, Univision=160).',
    )
    file_code = fields.Char(
        string='Filing Code',
        size=12,
        help='Short code used in SF Filing email subjects (e.g. ASC, BGC, PGC, RGC1, TGC, PTC, TC1, HUW, UNIC).',
    )


class MvDealPhase5(models.Model):
    _name = 'mv.deal'
    _inherit = ['mv.deal']

    def action_send_bundle_paperwork(self):
        """SF Workflow 12 — opens mail composer with the per-bundle paperwork template
        pre-filled, attaches the QWeb-rendered bundle paperwork PDF.
        """
        self.ensure_one()
        if not self.program or not getattr(self.program, 'is_bundle', False):
            raise UserError(_(
                "This Deal's Program is not flagged as a Bundle. "
                "Tick 'Bundle Program' on the Program record first, then set the paperwork recipients."
            ))
        recipients = (self.program.bundle_paperwork_to or '').strip()
        if not recipients:
            raise UserError(_(
                "No paperwork recipients configured on Program %s. "
                "Set 'Paperwork Recipients (TO)' before sending."
            ) % self.program.display_name)

        template = self.env.ref('marathon_ventures.mail_template_bundle_paperwork', raise_if_not_found=False)
        ctx = {
            'default_model': 'mv.deal',
            'default_res_ids': [self.id],
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'default_partner_ids': [],  # composer parses emails from 'To/Cc' below
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Bundle Paperwork'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }

    def action_send_traffic(self):
        """SF Workflow 12 — send Traffic instructions email (no rate disclosure)."""
        self.ensure_one()
        if not self.program or not getattr(self.program, 'traffic_email', False):
            raise UserError(_(
                "No Traffic Email configured on Program %s. "
                "Set it on the Program record before sending traffic."
            ) % (self.program.display_name if self.program else '—'))

        template = self.env.ref('marathon_ventures.mail_template_traffic', raise_if_not_found=False)
        ctx = {
            'default_model': 'mv.deal',
            'default_res_ids': [self.id],
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Traffic Instructions'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }

    def action_send_order_confirmation(self):
        """SF Workflow 29 — sends to the SF PDF signer pass-through address.

        Subject prefixes `@#effective` / `@#LTC` come from the user typing them
        in the mail composer; we pre-fill the To: address only.
        """
        self.ensure_one()
        template = self.env.ref('marathon_ventures.mail_template_order_confirmation', raise_if_not_found=False)
        ctx = {
            'default_model': 'mv.deal',
            'default_res_ids': [self.id],
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'default_subject': (
                # Reproduce SF subject minus Fwd: prefix
                self.name or 'Order'
            ),
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Order Confirmation'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }
