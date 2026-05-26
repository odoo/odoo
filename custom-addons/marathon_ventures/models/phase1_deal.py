# -*- coding: utf-8 -*-
"""Phase 1 — Deal lifecycle additions on top of the auto-generated mv.deal model.

What this layer adds:
  * Brand-approval + Finance-hold validations (SF Workflow 1 steps 1-3).
  * Default Status = 'sold' and Min Sep = 15 on create (Workflow 1 step 10/15).
  * One2many to schedules + Smart Button counts (schedule_count, total_booked_units,
    total_booked_dollars) for the Double Check Report rollups.
  * Smart-button actions:
      - action_new_schedule         (opens a child Schedule form with deal_parent set)
      - action_open_deal_revisions  (Phase 2 placeholder; raises a UserError for now)
      - action_send_filing_email    (opens a mail composer with the SF Filing subject)
  * Helper: _build_filing_subject() to reproduce the SF subject pattern.
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class MvDealPhase1(models.Model):
    _inherit = 'mv.deal'

    # ------------------------------------------------------------------
    # Relations / rollups (Double Check Report)
    # ------------------------------------------------------------------
    schedule_ids = fields.One2many(
        comodel_name='mv.schedules',
        inverse_name='deal_parent',
        string='Schedules',
    )
    schedule_count = fields.Integer(
        string='# Schedules',
        compute='_compute_schedule_rollups',
        store=True,
    )
    total_booked_units = fields.Float(
        string='Total Booked Units',
        compute='_compute_schedule_rollups',
        store=True,
        digits=(17, 1),
    )
    total_booked_dollars = fields.Monetary(
        string='Total Booked Dollars',
        compute='_compute_schedule_rollups',
        store=True,
        currency_field='currency_id',
    )

    @api.depends('schedule_ids', 'schedule_ids.units_available',
                 'schedule_ids.rate', 'schedule_ids.total_dollars',
                 'schedule_ids.status')
    def _compute_schedule_rollups(self):
        for deal in self:
            live = deal.schedule_ids.filtered(lambda s: s.status != 'canceled')
            deal.schedule_count = len(live)
            deal.total_booked_units = sum(live.mapped('units_available') or [0.0])
            deal.total_booked_dollars = sum(live.mapped('total_dollars') or [0.0])

    # ------------------------------------------------------------------
    # Validations (Workflow 1, steps 1-3 + general)
    # ------------------------------------------------------------------
    @api.constrains('brands', 'program', 'length')
    def _check_deal_create_preconditions(self):
        """Brand must be approved AND advertiser must not be on Finance hold."""
        for deal in self:
            # Skip checks on drafts that haven't picked a brand yet — those will
            # error out at form save time when user sees the field is required.
            if not deal.brands:
                continue
            brand = deal.brands
            if brand.approval_status not in ('approved',):
                raise ValidationError(_(
                    "Brand %(b)s is not Approved (current status: %(s)s). "
                    "Submit the brand for approval before creating a Deal."
                ) % {'b': brand.display_name, 's': dict(brand._fields['approval_status'].selection).get(brand.approval_status, '—')})

            # Advertiser hold check — look at the brand's advertiser
            advertiser = brand.advertiser
            if advertiser and getattr(advertiser, 'finance_hold', False):
                raise ValidationError(_(
                    "Advertiser %(a)s is on Finance hold (LOG / AOR / CIA required). "
                    "Resolve the hold before booking."
                ) % {'a': advertiser.display_name})

            # Length is a SF Selection picklist, validated by the field's selection list

    # ------------------------------------------------------------------
    # Defaults  (Workflow 1: status auto-set to Sold, min_sep default 15)
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('status', 'sold')
            if 'min_sep' not in vals or vals.get('min_sep') in (False, None):
                vals['min_sep'] = 'v_15'  # SF default: 15 minutes
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Smart Button actions
    # ------------------------------------------------------------------
    def action_new_schedule(self):
        """Smart Button — opens an mv.schedules form with deal_parent pre-set.

        Note: We intentionally do NOT pass a `default_networks` here. `networks`
        on mv.schedules is a Selection field (string keys like 'accuweather',
        'bounce', etc.), so passing a Many2one id from the Deal's program would
        raise `ValueError: Wrong value for mv.schedules.networks: <int>`. The
        `@api.onchange('deal_parent')` handler on mv.schedules safely auto-fills
        networks when the parent program's name matches a Selection key.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Schedule'),
            'res_model': 'mv.schedules',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_deal_parent': self.id,
            },
        }

    def action_open_schedules(self):
        """Smart Button — list of all schedules for this Deal."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedules — %s') % (self.name or ''),
            'res_model': 'mv.schedules',
            'view_mode': 'list,form',
            'domain': [('deal_parent', '=', self.id)],
            'context': {'default_deal_parent': self.id},
        }

    def action_open_deal_revisions(self):
        """Opens the 9-tab Deal Revisions wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deal Revisions — %s') % (self.name or ''),
            'res_model': 'mv.deal.revision.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_deal_id': self.id,
            },
        }

    # ------------------------------------------------------------------
    # Filing Email (SF Workflow 43)
    # ------------------------------------------------------------------
    def _build_filing_subject(self):
        """Reproduce the SF Filing email subject:
        `{program code} {quarter}{YY} - {advertiser} - {brand} :{length}`.
        """
        self.ensure_one()
        prog_code = ''
        if self.program:
            # mv.programs may not have a file_code yet; fall back to display_name truncated
            prog_code = (getattr(self.program, 'file_code', '') or '')[:8] or (self.program.display_name or '')[:8]
        adv = ''
        brand = ''
        if self.brands:
            brand = self.brands.display_name or ''
            if self.brands.advertiser:
                adv = self.brands.advertiser.display_name or ''
        # Quarter derived from current write date as a sensible default
        today = fields.Date.context_today(self)
        q = (today.month - 1) // 3 + 1
        yy = today.year % 100
        length_s = ''
        if self.length:
            try:
                length_s = ':' + str(int(str(self.length).replace('v_','')))
            except Exception:
                length_s = ':' + str(self.length)
        return f"{prog_code} {q}Q{yy:02d} - {adv} - {brand} {length_s}".strip()

    def action_send_filing_email(self):
        """Smart Button — opens mail composer with the SF Filing subject pre-filled."""
        self.ensure_one()
        template = self.env.ref('marathon_ventures.mail_template_filing', raise_if_not_found=False)
        ctx = {
            'default_model': 'mv.deal',
            'default_res_ids': [self.id],
            'default_use_template': bool(template),
            'default_template_id': template.id if template else False,
            'default_composition_mode': 'comment',
            'default_subject': self._build_filing_subject(),
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Send Filing Email'),
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'context': ctx,
        }
