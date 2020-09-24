# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

from datetime import datetime


class IrView(models.Model):
    _inherit = 'ir.ui.view'

    def write(self, vals):
        for view in self:
            # warn the user (only if at least one invoice is posted)
            # this is triggered when changing the arch of the view (mail template) is edited
            company = self.env['res.company'].search([('external_report_layout_id', '=', view.id)], limit=1)
            if company and 'arch_base' in vals:
                posted_move = self.env['account.move'].search([
                    ('state', '=', 'posted'),
                    ('move_type', 'in', ['out_invoice', 'out_receipt', 'in_refund']),
                    ('company_id', '=', company.id)
                ], limit=1)
                if posted_move:
                    mail_template = self.env.ref('account.document_layout_changed_template')
                    ctx = {
                        'user_name': self.env.user.name,
                        'company_name': company.name,
                        'timestamp': fields.Datetime.context_timestamp(self, datetime.now()).strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                    }
                    kwargs = {
                        'subject': _('Warning: document template of %s - %s has been modified', self._cr.dbname, company.name),
                        'partner_ids': self.env.user.partner_id.ids,
                        'body': mail_template._render(ctx, engine='ir.qweb', minimal_qcontext=True),
                        'notify_by_email': True,
                    }
                    self.env['mail.thread'].with_context(mail_notify_author=True).message_notify(**kwargs)
        return super(IrView, self).write(vals)
