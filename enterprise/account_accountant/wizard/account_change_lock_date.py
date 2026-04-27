from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools import date_utils

from odoo.addons.account.models.company import SOFT_LOCK_DATE_FIELDS, LOCK_DATE_FIELDS

from datetime import date, timedelta


class AccountChangeLockDate(models.TransientModel):
    """
    This wizard is used to change the lock date
    """
    _name = 'account.change.lock.date'
    _description = 'Change Lock Date'

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )

    fiscalyear_lock_date = fields.Date(
        string='Lock Everything',
        default=lambda self: self.env.company.fiscalyear_lock_date,
        help="Any entry up to and including that date will be postponed to a later time, in accordance with its journal's sequence.",
    )
    fiscalyear_lock_date_for_me = fields.Date(
        string='Lock Everything For Me',
        compute='_compute_lock_date_exceptions',
    )
    fiscalyear_lock_date_for_everyone = fields.Date(
        string='Lock Everything For Everyone',
        compute='_compute_lock_date_exceptions',
    )
    min_fiscalyear_lock_date_exception_for_me_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )
    min_fiscalyear_lock_date_exception_for_everyone_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )

    tax_lock_date = fields.Date(
        string="Lock Tax Return",
        default=lambda self: self.env.company.tax_lock_date,
        help="Any entry with taxes up to and including that date will be postponed to a later time, in accordance with its journal's sequence. "
             "The tax lock date is automatically set when the tax closing entry is posted.",
    )
    tax_lock_date_for_me = fields.Date(
        string='Lock Tax Return For Me',
        compute='_compute_lock_date_exceptions',
    )
    tax_lock_date_for_everyone = fields.Date(
        string='Lock Tax Return For Everyone',
        compute='_compute_lock_date_exceptions',
    )
    min_tax_lock_date_exception_for_me_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )
    min_tax_lock_date_exception_for_everyone_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )

    sale_lock_date = fields.Date(
        string='Lock Sales',
        default=lambda self: self.env.company.sale_lock_date,
        help="Any sales entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    sale_lock_date_for_me = fields.Date(
        string='Lock Sales For Me',
        compute='_compute_lock_date_exceptions',
    )
    sale_lock_date_for_everyone = fields.Date(
        string='Lock Sales For Everyone',
        compute='_compute_lock_date_exceptions',
    )
    min_sale_lock_date_exception_for_me_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )
    min_sale_lock_date_exception_for_everyone_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )

    purchase_lock_date = fields.Date(
        string='Lock Purchases',
        default=lambda self: self.env.company.purchase_lock_date,
        help="Any purchase entry prior to and including this date will be postponed to a later date, in accordance with its journal's sequence.",
    )
    purchase_lock_date_for_me = fields.Date(
        string='Lock Purchases For Me',
        compute='_compute_lock_date_exceptions',
    )
    purchase_lock_date_for_everyone = fields.Date(
        string='Lock Purchases For Everyone',
        compute='_compute_lock_date_exceptions',
    )
    min_purchase_lock_date_exception_for_me_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )
    min_purchase_lock_date_exception_for_everyone_id = fields.Many2one(
        comodel_name='account.lock_exception',
        compute='_compute_lock_date_exceptions',
    )

    hard_lock_date = fields.Date(
        string='Hard Lock',
        default=lambda self: self.env.company.hard_lock_date,
        help="Any entry up to and including that date will be postponed to a later time, in accordance with its journal sequence. "
             "This lock date is irreversible and does not allow any exception.",
    )
    current_hard_lock_date = fields.Date(
        string='Current Hard Lock',
        related='company_id.hard_lock_date',
        readonly=True,
    )

    exception_needed = fields.Boolean(  # TODO: remove in master (18.1)
        string='Exception needed',
        compute='_compute_exception_needed',
    )
    exception_needed_fields = fields.Char(
        # String of comma separated values of the field(s) the exception applies to
        compute='_compute_exception_needed_fields',
    )
    exception_applies_to = fields.Selection(
        string='Exception applies',
        selection=[
            ('me', "for me"),
            ('everyone', "for everyone"),
        ],
        default='me',
        required=True,
    )
    exception_duration = fields.Selection(
        string='Exception Duration',
        selection=[
            ('5min', "for 5 minutes"),
            ('15min', "for 15 minutes"),
            ('1h', "for 1 hour"),
            ('24h', "for 24 hours"),
            ('forever', "forever"),
        ],
        default='5min',
        required=True,
    )
    exception_reason = fields.Char(
        string='Exception Reason',
    )

    show_draft_entries_warning = fields.Boolean(
        string="Show Draft Entries Warning",
        compute='_compute_show_draft_entries_warning',
    )

    @api.depends('company_id')
    @api.depends_context('user', 'company')
    def _compute_lock_date_exceptions(self):
        for wizard in self:
            exceptions = self.env['account.lock_exception'].search(
                self.env['account.lock_exception']._get_active_exceptions_domain(wizard.company_id, SOFT_LOCK_DATE_FIELDS)
            )
            for field in SOFT_LOCK_DATE_FIELDS:
                field_exceptions = exceptions.filtered(lambda e: e.lock_date_field == field)
                field_exceptions_for_me = field_exceptions.filtered(lambda e: e.user_id.id == self.env.user.id)
                field_exceptions_for_everyone = field_exceptions.filtered(lambda e: not e.user_id.id)
                min_exception_for_me = min(field_exceptions_for_me, key=lambda e: e[field] or date.min) if field_exceptions_for_me else False
                min_exception_for_everyone = min(field_exceptions_for_everyone, key=lambda e: e[field] or date.min) if field_exceptions_for_everyone else False
                wizard[f"min_{field}_exception_for_me_id"] = min_exception_for_me
                wizard[f"min_{field}_exception_for_everyone_id"] = min_exception_for_everyone
                wizard[f"{field}_for_me"] = min_exception_for_me.lock_date if min_exception_for_me else False
                wizard[f"{field}_for_everyone"] = min_exception_for_everyone.lock_date if min_exception_for_everyone else False

    def _get_draft_moves_in_locked_period_domain(self):
        self.ensure_one()
        lock_date_domains = []
        if self.hard_lock_date:
            lock_date_domains.append([('date', '<=', self.hard_lock_date)])
        if self.fiscalyear_lock_date:
            lock_date_domains.append([('date', '<=', self.fiscalyear_lock_date)])
        if self.sale_lock_date:
            lock_date_domains.append([
                ('date', '<=', self.sale_lock_date),
                ('journal_id.type', '=', 'sale')])
        if self.purchase_lock_date:
            lock_date_domains.append([
                ('date', '<=', self.purchase_lock_date),
                ('journal_id.type', '=', 'purchase')])
        return [
            ('company_id', 'child_of', self.env.company.id),
            ('state', '=', 'draft'),
            *expression.OR(lock_date_domains),
        ]

    @api.depends('fiscalyear_lock_date', 'tax_lock_date', 'sale_lock_date', 'purchase_lock_date', 'hard_lock_date')
    def _compute_show_draft_entries_warning(self):
        for wizard in self:
            draft_entries = self.env['account.move'].search(self._get_draft_moves_in_locked_period_domain(), limit=1)
            wizard.show_draft_entries_warning = bool(draft_entries)

    def _get_changes_needing_exception(self):
        self.ensure_one()
        return {
            field: self[field]
            for field in SOFT_LOCK_DATE_FIELDS
            if self.env.company[field] and (not self[field] or self[field] < self.env.company[field])
        }

    @api.depends(*SOFT_LOCK_DATE_FIELDS)
    def _compute_exception_needed(self):
        # TODO: remove in master (18.1)
        for wizard in self:
            wizard.exception_needed = bool(wizard._get_changes_needing_exception())

    @api.depends(*SOFT_LOCK_DATE_FIELDS)
    def _compute_exception_needed_fields(self):
        for wizard in self:
            changes_needing_exception = wizard._get_changes_needing_exception()
            wizard.exception_needed_fields = ','.join(changes_needing_exception)

    def _prepare_lock_date_values(self, exception_vals_list=None):
        """
        Return a dictionary (lock date field -> field value)
        It only contains lock dates which are changed and for which no exception is added
        """
        self.ensure_one()
        if self.env.company.hard_lock_date and (not self.hard_lock_date or self.hard_lock_date < self.env.company.hard_lock_date):
            raise UserError(_('It is not possible to decrease or remove the Hard Lock Date.'))

        lock_date_values = {
            field: self[field]
            for field in LOCK_DATE_FIELDS
            if self[field] != self.env.company[field]
        }

        for field, lock_date in lock_date_values.items():
            if lock_date and lock_date > fields.Date.context_today(self):
                raise UserError(_('You cannot set a Lock Date in the future.'))

        # We do not change fields for which we add an exception
        if exception_vals_list:
            for exception_vals in exception_vals_list:
                for field in LOCK_DATE_FIELDS:
                    if field in exception_vals:
                        lock_date_values.pop(field, None)

        return lock_date_values

    def _prepare_exception_values(self):
        self.ensure_one()
        changes_needing_exception = self._get_changes_needing_exception()

        if not changes_needing_exception:
            return False

        # Exceptions for everyone and forever are just "normal" changes to the lock date.
        if self.exception_applies_to == 'everyone' and self.exception_duration == 'forever':
            return False

        exception_errors = []
        if not self.exception_applies_to:
            exception_errors.append(_('You need to select who the exception applies to.'))
        if not self.exception_duration:
            exception_errors.append(_('You need to select a duration for the exception.'))
        if exception_errors:
            raise UserError('\n'.join(exception_errors))

        exception_base_values = {
            'company_id': self.env.company.id,
        }

        exception_base_values['user_id'] = {
            'me': self.env.user.id,
            'everyone': False,
        }[self.exception_applies_to]

        exception_timedelta = {
            '5min': timedelta(minutes=5),
            '15min': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '24h': timedelta(hours=24),
            'forever': False,
        }[self.exception_duration]
        if exception_timedelta:
            exception_base_values['end_datetime'] = self.env.cr.now() + exception_timedelta

        if self.exception_reason:
            exception_base_values['reason'] = self.exception_reason

        exception_vals_list = [
            {
                **exception_base_values,
                field: value,
             }
            for field, value in changes_needing_exception.items()
        ]

        return exception_vals_list

    def _get_current_period_dates(self, lock_date_field):
        """ Gets the date_from - either the previous lock date or the start of the fiscal year.
        """
        self.ensure_one()
        company_lock_date = self.env.company[lock_date_field]
        if company_lock_date:
            date_from = company_lock_date + timedelta(days=1)
        else:
            date_from = date_utils.get_fiscal_year(self[lock_date_field])[0]
        return date_from, self[lock_date_field]

    def _create_default_report_external_values(self, lock_date_field):
        # to be overriden
        pass

    def _change_lock_date(self, lock_date_values=None):
        self.ensure_one()
        if lock_date_values is None:
            lock_date_values = self._prepare_lock_date_values()

        # Possibly create default report external values for tax
        tax_lock_date = lock_date_values.get('tax_lock_date', None)
        if tax_lock_date and tax_lock_date != self.env.company['tax_lock_date']:
            self._create_default_report_external_values('tax_lock_date')

        # Possibly create default report external values for fiscal year
        fiscalyear_lock_date = lock_date_values.get('fiscalyear_lock_date', None)
        hard_lock_date = lock_date_values.get('hard_lock_date', None)
        if fiscalyear_lock_date or hard_lock_date:
            fiscal_lock_date, field = max([
                (fiscalyear_lock_date, 'fiscalyear_lock_date'),
                (hard_lock_date, 'hard_lock_date'),
            ], key=lambda t: t[0] or date.min)
            company_fiscal_lock_date = max(
                self.env.company.fiscalyear_lock_date or date.min,
                self.env.company.hard_lock_date or date.min,
            )
            if fiscal_lock_date != company_fiscal_lock_date:
                self._create_default_report_external_values(field)

        self.env.company.sudo().write(lock_date_values)

    def change_lock_date(self):
        self.ensure_one()
        if self.env.user.has_group('account.group_account_manager'):
            exception_vals_list = self._prepare_exception_values()
            changed_lock_date_values = self._prepare_lock_date_values(exception_vals_list=exception_vals_list)

            if exception_vals_list:
                self.env['account.lock_exception'].create(exception_vals_list)

            self._change_lock_date(changed_lock_date_values)
        else:
            raise UserError(_('Only Billing Administrators are allowed to change lock dates!'))
        return {'type': 'ir.actions.act_window_close'}

    def action_show_draft_moves_in_locked_period(self):
        self.ensure_one()
        return {
            'view_mode': 'list',
            'name': _('Draft Entries'),
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'domain': self._get_draft_moves_in_locked_period_domain(),
            'search_view_id': [self.env.ref('account.view_account_move_filter').id, 'search'],
            'views': [[self.env.ref('account.view_move_tree_multi_edit').id, 'list'], [self.env.ref('account.view_move_form').id, 'form']],
        }

    def action_reopen_wizard(self):
        # This action can be used to keep the wizard open after doing something else
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _action_revoke_min_exception(self, exception_field):
        self.ensure_one()
        exception = self[exception_field]
        if exception:
            exception.action_revoke()
            self._compute_lock_date_exceptions()
        return self.action_reopen_wizard()

    def action_revoke_min_sale_lock_date_exception_for_me(self):
        return self._action_revoke_min_exception('min_sale_lock_date_exception_for_me_id')

    def action_revoke_min_purchase_lock_date_exception_for_me(self):
        return self._action_revoke_min_exception('min_purchase_lock_date_exception_for_me_id')

    def action_revoke_min_tax_lock_date_exception_for_me(self):
        return self._action_revoke_min_exception('min_tax_lock_date_exception_for_me_id')

    def action_revoke_min_fiscalyear_lock_date_exception_for_me(self):
        return self._action_revoke_min_exception('min_fiscalyear_lock_date_exception_for_me_id')

    def action_revoke_min_sale_lock_date_exception_for_everyone(self):
        return self._action_revoke_min_exception('min_sale_lock_date_exception_for_everyone_id')

    def action_revoke_min_purchase_lock_date_exception_for_everyone(self):
        return self._action_revoke_min_exception('min_purchase_lock_date_exception_for_everyone_id')

    def action_revoke_min_tax_lock_date_exception_for_everyone(self):
        return self._action_revoke_min_exception('min_tax_lock_date_exception_for_everyone_id')

    def action_revoke_min_fiscalyear_lock_date_exception_for_everyone(self):
        return self._action_revoke_min_exception('min_fiscalyear_lock_date_exception_for_everyone_id')
