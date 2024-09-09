from odoo import _, api, fields, models, Command
from odoo.tools import create_index
from odoo.tools.misc import format_datetime
from odoo.exceptions import UserError

from odoo.addons.account.models.company import SOFT_LOCK_DATE_FIELDS


class AccountLockException(models.Model):
    _name = "account.lock_exception"
    _description = "Account Lock Exception"

    active = fields.Boolean('Active', default=True)
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
        'End Date',
    )

    # Lock date fields; c.f. res.company
    # An unset lock date field means the exception does not change this field.
    # (It is not possible to remove a lock date completely).
    fiscalyear_lock_date = fields.Date(
        string="Global Lock Date",
        help="The date the Global Lock Date is set to by this exception. If no date is set the lock date is not changed.",
    )
    tax_lock_date = fields.Date(
        string="Tax Return Lock Date",
        help="The date the Tax Lock Date is set to by this exception. If no date is set the lock date is not changed.",
    )
    sale_lock_date = fields.Date(
        string='Lock Sales',
        help="The date the Sale Lock Date is set to by this exception. If no date is set the lock date is not changed.",
    )
    purchase_lock_date = fields.Date(
        string='Lock Purchases',
        help="The date the Purchase Lock Date is set to by this exception. If no date is set the lock date is not changed.",
    )

    def init(self):
        super().init()
        create_index(
            self.env.cr,
            indexname='account_lock_exception_company_id_end_datetime_idx',
            tablename=self._table,
            expressions=['company_id', 'user_id', 'end_datetime'],
            where="active = TRUE"
        )

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

    def _search_state(self, operator, value):
        if operator not in ['=', '!='] or value not in ['revoked', 'expired', 'active']:
            raise UserError(_('Operation not supported'))

        normal_domain_for_equals = []
        if value == 'revoked':
            normal_domain_for_equals = [
                ('active', '=', False),
            ]
        elif value == 'expired':
            normal_domain_for_equals = [
                '&',
                    ('active', '=', True),
                    ('end_datetime', '<', self.env.cr.now()),
            ]
        elif value == 'active':
            normal_domain_for_equals = [
                '&',
                    ('active', '=', True),
                    '|',
                        ('end_datetime', '=', None),
                        ('end_datetime', '>=', self.env.cr.now()),
            ]
        if operator == '=':
            return normal_domain_for_equals
        else:
            return ['!'] + normal_domain_for_equals

    @api.model_create_multi
    def create(self, vals_list):
        exceptions = super().create(vals_list)
        for exception in exceptions:
            company = exception.company_id
            changed_fields = [field for field in SOFT_LOCK_DATE_FIELDS if exception[field]]
            tracking_value_ids = []
            for field in changed_fields:
                value = exception[field]
                field_info = exception.fields_get([field])[field]
                tracking_values = self.env['mail.tracking.value']._create_tracking_values(
                    company[field], value, field, field_info, exception
                )
                tracking_value_ids.append(Command.create(tracking_values))
            self.env['res.company'].invalidate_model(fnames=[f'user_{field}' for field in changed_fields])
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
        return exceptions

    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a Lock Date Exception.'))

    def action_revoke(self):
        """Revokes an active exception."""
        if not self.env.user.has_group('account.group_account_manager'):
            raise UserError(_("You cannot revoke Lock Date Exceptions. Ask someone with the 'Adviser' role."))
        for record in self:
            if record.state == 'active':
                record_sudo = record.sudo()
                record_sudo.active = False
                record_sudo.end_datetime = fields.Datetime.now()
                fields_to_invalidate = [f'user_{field}' for field in SOFT_LOCK_DATE_FIELDS if record[field]]
                self.env['res.company'].invalidate_model(fnames=fields_to_invalidate)

    def _get_audit_trail_during_exception_domain(self):
        self.ensure_one()

        domain = [
            ('model', '=', 'account.move'),
            ('account_audit_log_activated', '=', True),
            ('message_type', '=', 'notification'),
            ('account_audit_log_move_id.company_id', 'child_of', self.company_id.id),  # WORKAROUND: record_company_id is not set for bills
            ('date', '>=', self.create_date),
        ]

        if self.user_id:
            domain.append(('create_uid', '=', self.user_id.id))
        if self.end_datetime:
            domain.append(('date', '<=', self.end_datetime))

        return domain

    def action_show_audit_trail_during_exception(self):
        self.ensure_one()
        return {
            'name': _("Audit Trail during the Exception"),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.message',
            'views': [(self.env.ref('account.view_message_tree_audit_log').id, 'list'), (False, 'form')],
            'search_view_id': [self.env.ref('account.view_message_tree_audit_log_search').id],
            'domain': self._get_audit_trail_during_exception_domain(),
        }
