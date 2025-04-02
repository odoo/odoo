from collections.abc import Iterator
import logging

from odoo import models, fields, api
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import ormcache
from odoo.tools.safe_eval import safe_eval, time
from odoo.tools.translate import _lt, _

_logger = logging.getLogger(__name__)

OPERATIONS = {
    'read': _lt("read"),
    'write': _lt("write"),
    'create': _lt("create"),
    'unlink': _lt("unlink"),
}

MODEL_ACCESS_ERROR = {
    'read': _lt("You are not allowed to access '%(document_kind)s' (%(document_model)s) records."),
    'write': _lt("You are not allowed to modify '%(document_kind)s' (%(document_model)s) records."),
    'create': _lt("You are not allowed to create '%(document_kind)s' (%(document_model)s) records."),
    'unlink': _lt("You are not allowed to delete '%(document_kind)s' (%(document_model)s) records."),
}

OPERATION_SELECTION = [
    ('r', 'Read'),
    ('w', 'Write'),
    ('rw', 'Read, Write'),
    ('c', 'Create'),
    ('rc', 'Read, Create'),
    ('wc', 'Write, Create'),
    ('rwc', 'Read, Write, Create'),
    ('d', 'Delete'),
    ('rd', 'Read, Delete'),
    ('wd', 'Write, Delete'),
    ('rwd', 'Read, Write, Delete'),
    ('cd', 'Create, Delete'),
    ('rcd', 'Read, Create, Delete'),
    ('wcd', 'Write, Create, Delete'),
    ('rwcd', 'Read, Write, Create, Delete'),
]


class IrAccess(models.Model):
    """ Access control records with domains. """
    _name = 'ir.access'
    _description = "Access"
    _order = 'model_id, group_id, id'
    _allow_sudo_commands = False

    name = fields.Char()
    active = fields.Boolean(default=True, help="Only active accesses are taken into account when checking access rights.")
    model_id = fields.Many2one('ir.model', string="Model", required=True, ondelete='cascade', index=True)
    group_id = fields.Many2one('res.groups', string="Group", ondelete='restrict', index=True)
    operation = fields.Selection(
        OPERATION_SELECTION, required=True, default='rwcd',
        help="Which operation(s) this access applies to, a subset of 'rwcd'.",
    )
    domain = fields.Char()

    for_read = fields.Boolean(
        compute='_compute_for_operation', search='_search_for_read',
        help="Whether this access record applies for operation 'read'",
    )
    for_write = fields.Boolean(
        compute='_compute_for_operation', search='_search_for_write',
        help="Whether this access record applies for operation 'write'",
    )
    for_create = fields.Boolean(
        compute='_compute_for_operation', search='_search_for_create',
        help="Whether this access record applies for operation 'create'",
    )
    for_unlink = fields.Boolean(
        compute='_compute_for_operation', search='_search_for_unlink',
        help="Whether this access record applies for operation 'unlink'",
    )

    @api.depends('operation')
    def _compute_for_operation(self):
        for access in self:
            operation = access.operation or ''
            access.for_read = 'r' in operation
            access.for_write = 'w' in operation
            access.for_create = 'c' in operation
            access.for_unlink = 'd' in operation

    def _search_for_read(self, operation, value):
        return self._search_for_operation('r', operation, value)

    def _search_for_write(self, operation, value):
        return self._search_for_operation('w', operation, value)

    def _search_for_create(self, operation, value):
        return self._search_for_operation('c', operation, value)

    def _search_for_unlink(self, operation, value):
        return self._search_for_operation('d', operation, value)

    def _search_for_operation(self, letter, operation, value) -> Domain:
        # determine the boolean(s) we test against
        assert operation in ('=', '!=', 'in', 'not in')
        bool_values = (
            {value} if operation == '=' else
            {not value} if operation == '!=' else
            {True, False} - set(value) if operation == 'not in' else
            set(value)
        )
        if len(bool_values) != 1:
            return Domain.TRUE if len(bool_values) == 2 else Domain.FALSE

        is_true = True in bool_values
        operations = [op for op, _ in OPERATION_SELECTION if (letter in op) == is_true]
        return Domain('operation', 'in', operations)

    @api.constrains('model_id')
    def _check_model_name(self):
        # Don't allow rules on rules records (this model).
        if any(access.model_id.model == self._name and access.domain for access in self):
            raise ValidationError(_('Accesses can not be applied on model Access itself.'))

    @api.constrains('active', 'domain', 'model_id')
    def _check_domain(self):
        eval_context = self._eval_context()
        for access in self:
            if access.active and access.domain:
                try:
                    domain = safe_eval(access.domain, eval_context)
                    model = self.env[access.model_id.model].sudo()
                    Domain(domain).validate(model)
                except Exception as e:
                    raise ValidationError(_('Invalid domain: %s', e))

    #
    # ormcache invalidation
    #
    def _clear_caches(self):
        """ Invalidate all the caches related to access rights. """
        self.env.invalidate_all()
        self.env.registry.clear_cache()

    @api.model_create_multi
    def create(self, vals_list):
        accesses = super().create(vals_list)
        self._clear_caches()
        return accesses

    def write(self, values):
        result = super().write(values)
        self._clear_caches()
        return result

    def unlink(self):
        result = super().unlink()
        self._clear_caches()
        return result

    @ormcache('self.env.uid', 'model_name', 'operation', 'tuple(self._get_access_context())')
    def _get_access_domain(self, model_name: str, operation: str) -> Domain | None:
        """ Return the domain that determines on which records of ``model_name``
        the current user is allowed to perform ``operation``.  The domain comes
        from the permissions and restrictions that applies to the current user.
        If no permission exists for the current user, the method returns ``None``.
        """
        assert operation in OPERATIONS, "Invalid access operation"

        accesses = self._get_access_records(model_name, operation)
        if not accesses.group_id:
            # no group access implies no permission at all
            return None

        # collect permissions and restrictions
        permissions = []
        restrictions = []
        eval_context = self._eval_context()
        for access in accesses:
            domain = Domain(safe_eval(access.domain, eval_context)) if access.domain else Domain.TRUE
            if access.group_id:
                permissions.append(domain)
            else:
                restrictions.append(domain)

        # add access for parent models as restrictions
        if operation == 'read':
            for parent_model_name, parent_field_name in self.env[model_name]._inherits.items():
                domain = self._get_access_domain(parent_model_name, operation)
                if domain is None:
                    return None
                if domain.is_true():
                    continue
                restrictions.append(Domain(parent_field_name, 'any', domain))

        return Domain.OR(permissions) & Domain.AND(restrictions)

    @ormcache('self.env.uid', 'model_name', 'operation', 'tuple(self._get_access_context())')
    def _get_restriction_domain(self, model_name: str, operation: str) -> Domain:
        """ Return the domain that combines the restrictions to perform
        ``operation`` on the records of ``model_name``.
        """
        assert operation in OPERATIONS, "Invalid access operation"

        domain = Domain([
            ('model_id', '=', self.env['ir.model']._get_id(model_name)),
            ('group_id', '=', False),
            (f'for_{operation}', '=', True),
            ('active', '=', True),
        ])
        accesses = self.sudo().search_fetch(domain, ['group_id', 'domain'], order='id')

        # collect restrictions
        eval_context = self._eval_context()
        restrictions = [
            Domain(safe_eval(access.domain, eval_context)) if access.domain else Domain.TRUE
            for access in accesses
        ]

        # add access for parent models as restrictions
        for parent_model_name, parent_field_name in self.env[model_name]._inherits.items():
            domain = self._get_access_domain(parent_model_name, operation)
            if domain is None:
                return Domain.FALSE
            restrictions.append(Domain(parent_field_name, 'any', domain))

        return Domain.AND(restrictions)

    def _get_access_records(self, model_name: str, operation: str):
        """ Returns all the accesses matching the given model for the operation
        for the current user.
        """
        model_id = self.env['ir.model']._get_id(model_name)
        group_ids = self.env.user._get_group_ids()
        domain = Domain([
            ('model_id', '=', model_id),
            ('group_id', 'in', [*group_ids, False]),
            (f'for_{operation}', '=', True),
            ('active', '=', True),
        ])
        return self.sudo().search_fetch(domain, ['group_id', 'domain'], order='id')

    def _get_access_context(self) -> Iterator:
        """ Return the context values that the evaluation of the access domain depends on. """
        yield tuple(self.env.context.get('allowed_company_ids', ()))

    def _eval_context(self):
        """Returns a dictionary to use as evaluation context for access domains.
       Note: ``company_ids`` contains the ids of the activated companies by the
       user with the switch company menu. These companies are filtered and trusted.
        """
        # use an empty context for 'user' to make the domain evaluation
        # independent from the context
        return {
            'user': self.env.user.with_context({}),
            'time': time,
            'company_ids': self.env.companies.ids,
            'company_id': self.env.company.id,
        }

    @ormcache('model_name', 'operation')
    def _get_access_groups(self, model_name, operation='read'):
        """ Return the group expression object that represents the users who
        can perform ``operation`` on model ``model_name``.
        """
        assert operation in OPERATIONS, "Invalid access operation"

        model_id = self.env['ir.model']._get_id(model_name)
        domain = [
            ('model_id', '=', model_id),
            ('group_id', '!=', False),
            (f'for_{operation}', '=', True),
            ('active', '=', True),
        ]
        accesses = self.sudo().search_fetch(domain, ['group_id'])

        group_definitions = self.env['res.groups']._get_group_definitions()
        return group_definitions.from_ids(accesses.group_id.ids)

    def _get_allowed_models(self, operation='read') -> set[str]:
        """ Return all the models for which the given operation is possible. """
        assert operation in OPERATIONS, "Invalid access operation"

        group_ids = self.env.user._get_group_ids()
        domain = Domain('access_ids', 'any', [
            ('active', '=', True),
            (f'for_{operation}', '=', True),
            ('group_id', 'in', group_ids),
        ])
        models = self.sudo().env['ir.model'].search_fetch(domain, ['model'], order='id')

        return set(models.mapped('model'))

    def _make_access_error(self, records, operation: str) -> AccessError:
        """ Return the exception to be raised in case of access error.
        Use an empty ``records`` if the current user has no permission at all to
        perform ``operation`` on the model.
        """
        if records:
            return self._make_record_access_error(records, operation)
        else:
            return self._make_model_access_error(records._name, operation)

    def _make_model_access_error(self, model_name: str, operation: str) -> AccessError:
        operation_error = str(MODEL_ACCESS_ERROR[operation]) % dict(
            document_kind=self.env['ir.model']._get(model_name).name or model_name,
            document_model=model_name,
        )

        groups = self._get_groups_with_access(model_name, operation)
        if groups:
            group_info = _(
                "This operation is allowed for the following groups:\n%(groups_list)s",
                groups_list="\n".join(f"\t- {group.display_name}" for group in groups),
            )
        else:
            group_info = _("No group currently allows this operation.")

        resolution_info = _("Contact your administrator to request access if necessary.")

        message = f"{operation_error}\n\n{group_info}\n\n{resolution_info}"
        return AccessError(message)

    def _get_groups_with_access(self, model_name: str, operation: str) -> models.Model:
        """ Return the groups that provide permissions for ``operation`` on ``model_name``. """
        assert operation in OPERATIONS, "Invalid access operation"

        model_id = self.env['ir.model']._get_id(model_name)
        domain = Domain('access_ids', 'any', [
            ('model_id', '=', model_id),
            (f'for_{operation}', '=', True),
            ('active', '=', True),
        ])
        return self.env['res.groups'].sudo().search_fetch(domain, ['display_name'])

    def _make_record_access_error(self, records, operation: str) -> AccessError:
        _logger.info(
            "Access Denied for operation: %s on record ids: %r, uid: %s, model: %s",
            operation, records.ids[:6], self.env.uid, records._name,
        )
        self = self.with_context(self.env.user.context_get())

        model_name = records._name
        model_description = self.env['ir.model']._get(model_name).name or model_name
        user_description = f"{self.env.user.name} (id={self.env.uid})"
        operation_error = _(
            "Uh-oh! Looks like you have stumbled upon some top-secret records.\n\n"
            "Sorry, %(user)s doesn't have '%(operation)s' access to:",
            user=user_description, operation=str(OPERATIONS[operation]),
        )
        failing_model = _(
            "- %(description)s (%(model)s)",
            description=model_description, model=model_name,
        )

        resolution_info = _(
            "If you really, really need access, perhaps you can win over your "
            "friendly administrator with a batch of freshly baked cookies."
        )

        # This extended AccessError is only displayed in debug mode.
        # Note that by default, public and portal users do not have the
        # group "base.group_no_one", even if debug mode is enabled, so it is
        # relatively safe here to include the list of accesses and record names.
        accesses = self._get_failed_accesses(records, operation)

        records_sudo = records[:6].sudo()
        company_related = any('company_id' in (access.domain or '') for access in accesses)

        def get_description(record):
            # If the user has access to the company of the record, add this
            # information in the description to help them to change company
            if company_related and 'company_id' in record and record.company_id in self.env.user.company_ids:
                return f'{model_description}, {record.display_name} ({model_name}: {record.id}, company={record.company_id.display_name})'
            return f'{model_description}, {record.display_name} ({model_name}: {record.id})'

        context = None
        if company_related:
            suggested_company = records_sudo._get_redirect_suggested_company()
            if suggested_company and len(suggested_company) > 1:
                resolution_info += "\n\n" + _(
                    "Note: this might be a multi-company issue. "
                    "Switching company may help - in Odoo, not in real life!"
                )
            elif suggested_company and suggested_company in self.env.user.company_ids:
                context = {'suggested_company': {
                    'id': suggested_company.id,
                    'display_name': suggested_company.display_name,
                }}
                resolution_info += "\n\n" + _(
                    "This seems to be a multi-company issue, you might be able "
                    "to access the record by switching to the company: %s.",
                    suggested_company.display_name,
                )
            elif suggested_company:
                resolution_info += "\n\n" + _(
                    "This seems to be a multi-company issue, but you do not "
                    "have access to the proper company to access the record anyhow."
                )

        if self.env.user.has_group('base.group_no_one') and self.env.user._is_internal():
            # this extended AccessError is only displayed in debug mode
            failing_records = '\n'.join(f'- {get_description(record)}' for record in records_sudo)
            access_description = '\n'.join(f'- {access.display_name}' for access in accesses)
            failing_rules = _("Blame the following accesses:\n%s", access_description)
            message = f"{operation_error}\n{failing_records}\n\n{failing_rules}\n\n{resolution_info}"
        else:
            message = f"{operation_error}\n{failing_model}\n\n{resolution_info}"

        # clean up the cache of records prefetched with display_name above
        records_sudo.invalidate_recordset()

        exception = AccessError(message)
        if context:
            exception.context = context
        return exception

    def _get_failed_accesses(self, records, operation: str):
        """ Return the access records for the given operation for the current
        user that fail on the given records.

        Can return any permission and/or restriction (since permissions are
        OR-ed together, the entire group succeeds or fails, while restrictions
        are AND-ed and can each fail independently.)
        """
        model = records.browse(()).sudo().with_context(active_test=False)
        eval_context = self._eval_context()

        accesses = self._get_access_records(model._name, operation)

        # first check if the permissions fail for any record (aka if searching
        # on (records, permissions) filters out some of the records)
        permissions = accesses.filtered('group_id')
        permission_domain = Domain.OR(
            Domain(safe_eval(access.domain, eval_context)) if access.domain else Domain.TRUE
            for access in permissions
        )
        # if all records get returned, the group accesses are not failing
        if len(records.sudo().filtered_domain(permission_domain)) == len(records):
            permissions = self.browse()

        # failing accesses are previously selected permissions or any failing restriction
        def is_failing(access):
            if access.group_id:
                return access in permissions
            domain = Domain(safe_eval(access.domain, eval_context)) if access.domain else Domain.TRUE
            return len(records.sudo().filtered_domain(domain)) < len(records)

        return accesses.filtered(is_failing)
