from odoo import _, api, fields, models
from odoo.fields import Command, Domain
from odoo.tools.misc import format_datetime
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account.models.company import SOFT_LOCK_DATE_FIELDS

from datetime import date


class AccountLock_Exception(models.Model):
    _name = 'account.lock_exception'
    _description = "Account Lock Exception"

    active = fields.Boolean(
        string='Active',
        default=True,
    )
    state = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('revoked', 'Revoked'),
            ('expired', 'Expired'),
        ],
        string="State",
        compute='_compute_state',
        search='_search_state'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    # An exception w/o user_id is an exception for everyone
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user,
    )
    reason = fields.Char(
        string='Reason',
    )
    # An exception without `end_datetime` is valid forever
    end_datetime = fields.Datetime(
        string='End Date',
    )

    # The changed lock date
    lock_date_field = fields.Selection(
        selection=[
            ('fiscalyear_lock_date', 'Global Lock Date'),
            ('tax_lock_date', 'Tax Return Lock Date'),
            ('sale_lock_date', 'Sales Lock Date'),
            ('purchase_lock_date', 'Purchase Lock Date'),
        ],
        string="Lock Date Field",
        required=True,
        help="Technical field identifying the changed lock date",
    )
    lock_date = fields.Date(
        string="Changed Lock Date",
        help="Technical field giving the date the lock date was changed to.",
    )
    company_lock_date = fields.Date(
        string="Original Lock Date",
        copy=False,
        help="Technical field giving the date the company lock date at the time the exception was created.",
    )

    # (Non-stored) computed lock date fields; c.f. res.company
    fiscalyear_lock_date = fields.Date(
        string="Global Lock Date",
        compute="_compute_lock_dates",
        search="_search_fiscalyear_lock_date",
        help="The date the Global Lock Date is set to by this exception. If the lock date is not changed it is set to the maximal date.",
    )
    tax_lock_date = fields.Date(
        string="Tax Return Lock Date",
        compute="_compute_lock_dates",
        search="_search_tax_lock_date",
        help="The date the Tax Lock Date is set to by this exception. If the lock date is not changed it is set to the maximal date.",
    )
    sale_lock_date = fields.Date(
        string='Sales Lock Date',
        compute="_compute_lock_dates",
        search="_search_sale_lock_date",
        help="The date the Sale Lock Date is set to by this exception. If the lock date is not changed it is set to the maximal date.",
    )
    purchase_lock_date = fields.Date(
        string='Purchase Lock Date',
        compute="_compute_lock_dates",
        search="_search_purchase_lock_date",
        help="The date the Purchase Lock Date is set to by this exception. If the lock date is not changed it is set to the maximal date.",
    )

    _company_id_end_datetime_idx = models.Index("(company_id, user_id, end_datetime) WHERE active IS TRUE")

    def _compute_display_name(self):
        for record in self:
            record.display_name = _("Lock Date Exception %s", record.id)

    @api.depends('active', 'end_datetime')
    def _compute_state(self):
        for record in self:
            if not record.active:
                record.state = 'revoked'
            elif record.end_datetime and record.end_datetime < self.env.cr.now():
                record.state = 'expired'
            else:
                record.state = 'active'

    @api.depends('lock_date_field', 'lock_date')
    def _compute_lock_dates(self):
        for exception in self:
            for field in SOFT_LOCK_DATE_FIELDS:
                if field == exception.lock_date_field:
                    exception[field] = exception.lock_date
                else:
                    exception[field] = date.max

    def _search_state(self, operator, value):
        if operator != 'in':
            return NotImplemented

        domain = Domain.FALSE
        if 'revoked' in value:
            domain |= Domain('active', '=', False)
        if 'expired' in value:
            domain |= Domain('active', '=', True) & Domain('end_datetime', '<', self.env.cr.now())
        if 'active' in value:
            domain |= Domain('active', '=', True) & (Domain('end_datetime', '=', False) | Domain('end_datetime', '>=', self.env.cr.now()))
        return domain

    def _search_lock_date(self, field, operator, value):
        if operator not in ['<', '<='] or not value:
            return NotImplemented
        return ['&',
                  ('lock_date_field', '=', field),
                  '|',
                      ('lock_date', '=', False),
                      ('lock_date', operator, value),
               ]

    def _search_fiscalyear_lock_date(self, operator, value):
        return self._search_lock_date('fiscalyear_lock_date', operator, value)

    def _search_tax_lock_date(self, operator, value):
        return self._search_lock_date('tax_lock_date', operator, value)

    def _search_sale_lock_date(self, operator, value):
        return self._search_lock_date('sale_lock_date', operator, value)

    def _search_purchase_lock_date(self, operator, value):
        return self._search_lock_date('purchase_lock_date', operator, value)

    def _invalidate_affected_user_lock_dates(self):
        affected_lock_date_fields = {exception.lock_date_field for exception in self}
        self.env['res.company'].invalidate_model(
            fnames=[f'user_{field}' for field in list(affected_lock_date_fields)],
        )

    @api.model_create_multi
    def create(self, vals_list):
        # Preprocess arguments:
        # 1. Parse lock date arguments
        #   E.g. to create an exception for 'fiscalyear_lock_date' to '2024-01-01' put
        #   {'fiscalyear_lock_date': '2024-01-01'} in the create vals.
        #   The same thing works for all other fields in SOFT_LOCK_DATE_FIELDS.
        # 2. Fetch company lock date
        for vals in vals_list:
            if 'lock_date' not in vals or 'lock_date_field' not in vals:
                # Use vals[field] (for field in SOFT_LOCK_DATE_FIELDS) to init the data
                changed_fields = [field for field in SOFT_LOCK_DATE_FIELDS if field in vals]
                if len(changed_fields) != 1:
                    raise ValidationError(_("A single exception must change exactly one lock date field."))
                field = changed_fields[0]
                vals['lock_date_field'] = field
                vals['lock_date'] = vals.pop(field)
            company = self.env['res.company'].browse(vals.get('company_id', self.env.company.id))
            if 'company_lock_date' not in vals:
                vals['company_lock_date'] = company[vals['lock_date_field']]

        exceptions = super().create(vals_list)

        # Log the creation of the exception and the changed field on the company chatter
        for exception in exceptions:
            company = exception.company_id

            # Create tracking values to display the lock date change in the chatter
            field = exception.lock_date_field
            value = exception.lock_date
            field_info = exception.fields_get([field])[field]
            tracking_values = self.env['mail.tracking.value']._create_tracking_values(
                company[field], value, field, field_info, exception,
            )
            tracking_value_ids = [Command.create(tracking_values)]

            # In case there is no explicit end datetime "forever" is implied by not mentioning an end datetime
            end_datetime_string = _(" valid until %s", format_datetime(self.env, exception.end_datetime)) if exception.end_datetime else ""
            reason_string = _(" for '%s'", exception.reason) if exception.reason else ""
            company_chatter_message = _(
                "%(exception)s for %(user)s%(end_datetime_string)s%(reason)s.",
                exception=exception._get_html_link(title=_("Exception")),
                user=exception.user_id.display_name if exception.user_id else _("everyone"),
                end_datetime_string=end_datetime_string,
                reason=reason_string,
            )
            company.sudo().message_post(
                body=company_chatter_message,
                tracking_value_ids=tracking_value_ids,
            )

        exceptions._invalidate_affected_user_lock_dates()
        return exceptions

    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a Lock Date Exception.'))

    def _recreate(self):
        """
        1. Copy all exceptions in self but update the company lock date.
        2. Revoke all exceptions in self.
        3. Return the new records from step 1.
        """
        if not self:
            return self.env['account.lock_exception']
        vals_list = self.with_context(active_test=False).copy_data()
        new_records = self.create(vals_list)
        self.sudo().action_revoke()
        return new_records

    def action_revoke(self):
        """Revokes an active exception."""
        if not self.env.user.has_group('account.group_account_manager') and not self.env.su:
            raise UserError(_("You cannot revoke Lock Date Exceptions. Ask someone with the 'Adviser' role."))
        for record in self:
            if record.state == 'active':
                record_sudo = record.sudo()
                record_sudo.active = False
                record_sudo.end_datetime = fields.Datetime.now()
                record._invalidate_affected_user_lock_dates()

    @api.model
    def _get_active_exceptions_domain(self, company, soft_lock_date_fields):
        return (
            Domain.OR(
                Domain(field, '<', company[field])
                for field in soft_lock_date_fields
                if company[field]
            )
            & Domain('company_id', '=', company.id)
            & Domain('state', '=', 'active'),  # checks the datetime
        )

    def _get_audit_trail_during_exception_domain(self):
        self.ensure_one()

        common_message_domain = [
            ('date', '>=', self.create_date),
        ]
        if self.user_id:
            common_message_domain.append(('create_uid', '=', self.user_id.id))
        if self.end_datetime:
            common_message_domain.append(('date', '<=', self.end_datetime))

        # Add restrictions on the accounting date to avoid unnecessary entries
        min_date = self.lock_date
        max_date = self.company_lock_date
        move_date_domain = []
        tracking_old_datetime_domain = []
        tracking_new_datetime_domain = []
        if min_date:
            move_date_domain.append([('date', '>=', min_date)])
            tracking_old_datetime_domain.append([('tracking_value_ids.old_value_datetime', '>=', min_date)])
            tracking_new_datetime_domain.append([('tracking_value_ids.new_value_datetime', '>=', min_date)])
        if max_date:
            move_date_domain.append([('date', '<=', max_date)])
            tracking_old_datetime_domain.append([('tracking_value_ids.old_value_datetime', '<=', max_date)])
            tracking_new_datetime_domain.append([('tracking_value_ids.new_value_datetime', '<=', max_date)])

        return [
            ('company_id', 'child_of', self.company_id.id),
            ('audit_trail_message_ids', 'any', common_message_domain),
            '|',
                # The date was changed from or to a value inside the excepted period
                ('audit_trail_message_ids', 'any', [
                    ('tracking_value_ids.field_id', '=', self.env['ir.model.fields']._get('account.move', 'date').id),
                    '|',
                        *Domain.AND(tracking_old_datetime_domain),
                        *Domain.AND(tracking_new_datetime_domain),
                ]),
                # The date of the move is inside the excepted period and sth. was changed on the move
                *Domain.AND(move_date_domain),
        ]

    def action_show_audit_trail_during_exception(self):
        self.ensure_one()
        return {
            'name': _("Journal Items"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('move_id', 'any', self._get_audit_trail_during_exception_domain())],
       }
