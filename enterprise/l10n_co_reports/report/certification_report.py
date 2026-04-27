# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models, fields
from odoo.exceptions import UserError
from odoo.tools.translate import _


class CertificationReport(models.AbstractModel):
    _name = 'report.l10n_co_reports.report_certification'
    _description = "Colombian Certification Report"

    def _get_report_values(self, docids, data=None):
        docs = []
        partner_doc = None
        options = self._context.get('options')
        report = self.env['account.report'].browse(options['report_id'])
        lines = report._filter_out_folded_children(report._get_lines(options))

        for line in lines:
            model, model_id = report._get_model_info_from_id(line['id'])
            if model == 'res.partner':
                # The lines are always grouped by partner, and the partner lines always come first.
                # So the partner_doc dict can be initialized here within the 'if'.
                partner_doc = {
                    'partner_id': self.env[model].browse(model_id),
                    'lines': [],
                }

                # Add totals
                for i, column in enumerate(line['columns']):
                    column_data = options['columns'][i % len(options['columns'])]
                    partner_doc[column_data['expression_label']] = column.get('name')
                docs.append(partner_doc)
            else:
                line_dict = {}
                for i, column in enumerate(line['columns']):
                    column_data = options['columns'][i % len(options['columns'])]
                    line_dict[column_data['expression_label']] = column.get('name')
                # As mentioned above, at this stage of the iteration,
                # the partner_doc dict (and the 'lines' key) will always be set.
                partner_doc['lines'].append(line_dict)

        # Get rid of partners without expanded lines.
        docs = [doc for doc in docs if doc['lines']]
        if not docs:
            raise UserError(_('You have to expand at least one partner.'))

        date_from = options.get('date', {}).get('date_from') or data['wizard_values'].get("declaration_date")
        current_date = fields.Datetime.to_datetime(date_from) or datetime.now()
        return {
            'docs': docs,
            'options': data['wizard_values'],
            'report_name': 'report_%s' % report.get_external_id()[report.id],
            'company': self.env.company,
            'current_year': self.env.company.compute_fiscalyear_dates(current_date)['date_from'].year,
        }
