# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import models, fields
from odoo.exceptions import UserError
from odoo.tools.translate import _


class LibroDiarioReport(models.AbstractModel):
    _name = 'report.l10n_co_reports.report_libro_diario'
    _description = "Colombian Libro Diario Report"

    def _get_report_values(self, docids, data=None):
        options = self._context.get('options')
        report = self.env['account.report'].browse(options['report_id'])
        lines = report._filter_out_folded_children(report._get_lines(options))

        doc = {'lines': []}
        labels = [column['expression_label'] for column in options['columns']]
        for line in lines:
            values = [column.get('name') for column in line['columns']]
            doc['lines'].append(dict(zip(labels, values)))
        if not doc['lines']:
            raise UserError(_('No lines were provided to print.'))

        return {
            'docs': [doc],
            'options': data,
            'report_name': 'report_%s' % report.get_external_id()[report.id],
            'company': self.env.company,
            'date_range': [options['date']['date_from'], min(options['date']['date_to'], str(datetime.now().date()))],
        }
