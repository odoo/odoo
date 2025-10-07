# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import logging
import typing

from odoo import _, api, fields, models, tools
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import config, frozendict
from odoo.tools.safe_eval import safe_eval, time


_logger = logging.getLogger(__name__)


class RuleInfo(typing.NamedTuple):
    rule_id: int
    group_id: int
    domain: Domain | str


class IrRule(models.Model):
    _name = 'ir.rule'
    _description = 'Record Rule'
    _order = 'model_id DESC,id'
    _MODES = ('read', 'write', 'create', 'unlink')
    _allow_sudo_commands = False

    name = fields.Char()
    active = fields.Boolean(default=True, help="If you uncheck the active field, it will disable the record rule without deleting it (if you delete a native record rule, it may be re-created when you reload the module).")
    model_id = fields.Many2one('ir.model', string='Model', index=True, required=True, ondelete="cascade")
    groups = fields.Many2many('res.groups', 'rule_group_rel', 'rule_group_id', 'group_id', ondelete='restrict')
    domain_force = fields.Text(string='Domain')
    perm_read = fields.Boolean(string='Read', default=True)
    perm_write = fields.Boolean(string='Write', default=True)
    perm_create = fields.Boolean(string='Create', default=True)
    perm_unlink = fields.Boolean(string='Delete', default=True)

    _no_access_rights = models.Constraint(
        'CHECK (perm_read!=False or perm_write!=False or perm_create!=False or perm_unlink!=False)',
        "Rule must have at least one checked access right!",
    )

    @api.model
    def _eval_context(self):
        """Returns a dictionary to use as evaluation context for
           ir.rule domains.
           Note: company_ids contains the ids of the activated companies
           by the user with the switch company menu. These companies are
           filtered and trusted.
        """
        # use an empty context for 'user' to make the domain evaluation
        # independent from the context
        return {
            'user': self.env.user.with_context({}),
            'company_ids': self.env.companies.ids,
            'company_id': self.env.company.id,
        }

    @api.depends('groups')
    def _compute_global(self):
        for rule in self:
            rule['global'] = not rule.groups

    @api.constrains('model_id')
    def _check_model_name(self):
        # Don't allow rules on rules records (this model).
        if any(rule.model_id.model == self._name for rule in self):
            raise ValidationError(_('Rules can not be applied on the Record Rules model.'))

    @api.constrains('active', 'domain_force', 'model_id')
    def _check_domain(self):
        eval_context = self._eval_context()
        for rule in self:
            if rule.active and rule.domain_force:
                try:
                    domain = safe_eval(rule.domain_force, eval_context)
                    model = self.env[rule.model_id.model].sudo()
                    Domain(domain).validate(model)
                except Exception as e:
                    raise ValidationError(_('Invalid domain: %s', e))

    def _compute_domain_keys(self):
        """ Return the list of context keys to use for caching ``_compute_domain``. """
        return ['allowed_company_ids']

    def _get_failing(self, for_records, mode='read'):
        """ Returns the rules for the mode for the current user which fail on
        the specified records.

        Can return any global rule and/or all local rules (since local rules
        are OR-ed together, the entire group succeeds or fails, while global
        rules get AND-ed and can each fail)
        """
        Model = for_records.browse(()).sudo()
        record_ids = for_records.ids
        eval_context = self._eval_context()
        failing_ids = set()
        all_rules = self._get_rules(Model._name)[mode]

        # first check if the group rules fail for any record (aka if
        # searching on (records, group_rules) filters out some of the records)
        user_group_ids = set(self.env.user._get_group_ids())
        group_domains = Domain.OR(
            r.domain if isinstance(r.domain, Domain) else Domain(safe_eval(r.domain, eval_context))
            for r in all_rules
            if r.group_id in user_group_ids
        )

        # if all records get returned, the group rules are not failing
        if Model.search_count(group_domains & Domain('id', 'in', record_ids)) < len(record_ids):
            failing_ids.update(r.rule_id for r in all_rules if r.group_id in user_group_ids)

        # check failing global rules
        for r in all_rules:
            if r.group_id:
                continue
            dom = r.domain if isinstance(r.domain, Domain) else Domain(safe_eval(r.domain, eval_context))
            if Model.search_count(dom & Domain('id', 'in', record_ids)) < len(record_ids):
                failing_ids.add(r.rule_id)

        return self.browse(id_ for r in all_rules if (id_ := r.rule_id) in failing_ids)

    @api.model
    @tools.ormcache('model_name', cache='stable')
    def _get_rules(self, model_name: str) -> dict[str, tuple[RuleInfo, ...]]:
        """ Returns all the rules matching the model for the mode for the
        current user.
        """
        model = self.env[model_name]
        all_rules = self.sudo().search_fetch(
            [
                ('active', '=', True),
                ('model_id.model', '=', model_name),
            ],
            ['groups', 'domain_force', *(f'perm_{mode}' for mode in self._MODES)],
            order='id',
        )
        domains = {}
        for rule in all_rules:
            domain = (rule.domain_force or '').strip()
            try:
                if domain:
                    domain = ast.literal_eval(domain)
                else:
                    domain = Domain.TRUE
            except ValueError:
                domains[rule] = domain
            else:
                domains[rule] = Domain(domain).optimize(model)
        return frozendict({
            mode: tuple(
                RuleInfo(rule.id, group.id, domains[rule])
                for rule in all_rules.filtered(f'perm_{mode}')
                # iterate over all rules, or just once with an empty groups recordset for global rules
                for group in rule.groups or (rule.groups,)
            )
            for mode in self._MODES
        })

    @api.model
    @tools.conditional(
        'xml' not in config['dev_mode'],
        tools.ormcache('self.env.uid', 'self.env.su', 'model_name', 'mode',
                       'tuple(self._compute_domain_context_values())'),
    )
    def _compute_domain(self, model_name: str, mode: str = "read") -> Domain:
        model = self.env[model_name]
        if self.env.su:
            return Domain.TRUE

        # add rules for parent models
        global_domains: list[Domain] = []
        group_domains: list[Domain] = []
        for parent_model_name, parent_field_name in model._inherits.items():
            if not model._fields[parent_field_name].store:
                continue
            if domain := self._compute_domain(parent_model_name, mode):
                global_domains.append(Domain(parent_field_name, 'any', domain))

        # fetch the rules
        all_rules = self._get_rules(model_name)[mode]
        if all_rules:
            # filter rules which apply
            user_group_ids = set(self.env.user._get_group_ids())
            user_group_ids.add(False)  # global rule
            # evaluate the domains
            eval_context = None
            for rule in all_rules:
                if rule.group_id not in user_group_ids:
                    continue
                domain = rule.domain
                if not isinstance(domain, Domain):
                    if eval_context is None:
                        eval_context = self._eval_context()
                    domain = Domain(safe_eval(domain, eval_context))
                if rule.group_id:
                    group_domains.append(domain)
                else:
                    global_domains.append(domain)

        # combine global domains and group domains
        if group_domains:
            global_domains.append(Domain.OR(group_domains))
        return Domain.AND(global_domains).optimize(model)

    def _compute_domain_context_values(self):
        for k in self._compute_domain_keys():
            v = self.env.context.get(k)
            if isinstance(v, list):
                # currently this could be a frozenset (to avoid depending on
                # the order of allowed_company_ids) but it seems safer if
                # possibly slightly more miss-y to use a tuple
                v = tuple(v)
            yield v

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache('stable')
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        # DLE P33: tests
        self.env.flush_all()
        self.env.registry.clear_cache('stable')
        return res

    def write(self, vals):
        res = super().write(vals)
        # DLE P33: tests
        # - odoo/addons/test_access_rights/tests/test_feedback.py
        # - odoo/addons/test_access_rights/tests/test_ir_rules.py
        # - odoo/addons/base/tests/test_orm.py (/home/dle/src/odoo/master-nochange-fp/odoo/addons/base/tests/test_orm.py)
        self.env.flush_all()
        self.env.registry.clear_cache('stable')
        return res

    def _make_access_error(self, operation, records):
        _logger.info('Access Denied by record rules for operation: %s on record ids: %r, uid: %s, model: %s', operation, records.ids[:6], self.env.uid, records._name)
        self = self.with_context(self.env.user.context_get())

        model = records._name
        description = self.env['ir.model']._get(model).name or model
        operations = {
            'read':  _("read"),
            'write': _("write"),
            'create': _("create"),
            'unlink': _("unlink"),
        }
        user_description = f"{self.env.user.name} (id={self.env.user.id})"
        operation_error = _("Uh-oh! Looks like you have stumbled upon some top-secret records.\n\n" \
            "Sorry, %(user)s doesn't have '%(operation)s' access to:", user=user_description, operation=operations[operation])
        failing_model = _("- %(description)s (%(model)s)", description=description, model=model)

        resolution_info = _("If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.")

        # Note that by default, public and portal users do not have
        # the group "base.group_no_one", even if debug mode is enabled,
        # so it is relatively safe here to include the list of rules and record names.
        rules = self._get_failing(records, mode=operation).sudo()

        display_records = records[:6].sudo()
        company_related = any('company_id' in (r.domain_force or '') for r in rules)

        def get_record_description(rec):
            # If the user has access to the company of the record, add this
            # information in the description to help them to change company
            if company_related and 'company_id' in rec and rec.company_id in self.env.user.company_ids:
                return f'{description}, {rec.display_name} ({model}: {rec.id}, company={rec.company_id.display_name})'
            return f'{description}, {rec.display_name} ({model}: {rec.id})'

        context = None
        if company_related:
            suggested_companies = display_records._get_redirect_suggested_company()
            if suggested_companies and len(suggested_companies) != 1:
                resolution_info += _('\n\nNote: this might be a multi-company issue. Switching company may help - in Odoo, not in real life!')
            elif suggested_companies and suggested_companies in self.env.user.company_ids:
                context = {'suggested_company': {'id': suggested_companies.id, 'display_name': suggested_companies.display_name}}
                resolution_info += _('\n\nThis seems to be a multi-company issue, you might be able to access the record by switching to the company: %s.', suggested_companies.display_name)
            elif suggested_companies:
                resolution_info += _('\n\nThis seems to be a multi-company issue, but you do not have access to the proper company to access the record anyhow.')

        if not self.env.user.has_group('base.group_no_one') or not self.env.user._is_internal():
            msg = f"{operation_error}\n{failing_model}\n\n{resolution_info}"
        else:
            # This extended AccessError is only displayed in debug mode.
            failing_records = '\n'.join(f'- {get_record_description(rec)}' for rec in display_records)
            rules_description = '\n'.join(f'- {rule.name}' for rule in rules)
            failing_rules = _("Blame the following rules:\n%s", rules_description)
            msg = f"{operation_error}\n{failing_records}\n\n{failing_rules}\n\n{resolution_info}"

        # clean up the cache of records because of filtered_domain to check ir.rule + display_name above
        records.invalidate_recordset()

        exception = AccessError(msg)
        if context:
            exception.context = context
        return exception


#
# Hack for field 'global': this field cannot be defined like others, because
# 'global' is a Python keyword. Therefore, we add it to the class by assignment.
# Note that the attribute '_module' is normally added by the class' metaclass.
#
global_ = fields.Boolean(compute='_compute_global', store=True,
                         help="If no group is specified the rule is global and applied to everyone")
setattr(IrRule, 'global', global_)
global_.__set_name__(IrRule, 'global')
