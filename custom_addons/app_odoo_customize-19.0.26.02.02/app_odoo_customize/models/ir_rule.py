# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, tools, _
from odoo.http import request

_logger = logging.getLogger(__name__)
class IrRule(models.Model):
    _inherit = 'ir.rule'
    

    def _make_access_error(self, operation, records):
        # todo: 当前此处不生效
        if self.env.user.has_group('base.group_no_one'):
            # 在用户端处理更详细的错误信息
            _logger.warning('Access Denied by record rules for operation: %s on record ids: %r, uid: %s, model: %s', operation, records.ids[:6], self._uid, records._name)
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
            operation_error = _("Debug Info! Looks like you have stumbled upon some top-secret records.\n\n" \
                "Sorry, %(user)s doesn't have '%(operation)s' access to:", user=user_description, operation=operations[operation])
            failing_model = _("- %(description)s (%(model)s), ids:[%(ids)r]", description=description, model=model, ids=records.ids[:6])
    
            resolution_info = _("If you really, really need access, perhaps you can win over your friendly administrator with a batch of freshly baked cookies.")
    
            rules = self._get_failing(records, mode=operation).sudo()
    
            records_sudo = records[:6].sudo()
            company_related = any('company_id' in (r.domain_force or '') for r in rules)
    
            def get_record_description(rec):
                # If the user has access to the company of the record, add this
                # information in the description to help them to change company
                if company_related and 'company_id' in rec and rec.company_id in self.env.user.company_ids:
                    return f'{description}, {rec.display_name} ({model}: {rec.id}, company={rec.company_id.display_name})'
                return f'{description}, {rec.display_name} ({model}: {rec.id})'
    
            context = None
            if company_related:
                suggested_companies = records_sudo._get_redirect_suggested_company()
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
                failing_records = '\n'.join(f'- {get_record_description(rec)}' for rec in records_sudo)
                rules_description = '\n'.join(f'- {rule.name}' for rule in rules)
                failing_rules = _("Blame the following rules:\n%s", rules_description)
                msg = f"{operation_error}\n{failing_records}\n\n{failing_rules}\n\n{resolution_info}"
    
            # clean up the cache of records prefetched with display_name above
            records_sudo.invalidate_recordset()
    
            exception = AccessError(msg)
            if context:
                exception.context = context
            return exception

        return super(IrRule, self)._make_access_error(operation, records)
