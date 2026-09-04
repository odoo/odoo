import markupsafe

from odoo import models
from odoo.tools import html_sanitize


class ReportLabelBase(models.AbstractModel):
    _name = 'report.product.label.base'
    _description = 'Base Label Report'

    _label_defaults = {
        'barcode_type': 'barcode',
        'barcode_value': '',
        'barcode_text': '',
        'copies': 1,
        'extra_content': '',
        'name': '',
        'primary_value': '',
        'reference': '',
        'secondary_text': '',
        'secondary_value': '',
        'secondary_value_suffix': '',
    }

    def _prepare_invisible_label(self):
        return {'invisible': True}

    def _prepare_rendering_labels(self, labels):
        rendering_labels = []
        for label in labels:
            rendering_label = {
                **self._label_defaults,
                **label,
                'invisible': False,
            }
            rendering_label['extra_content'] = html_sanitize(label.get('extra_content') or '')
            rendering_labels.append(rendering_label)
        return rendering_labels

    def _expand_labels(self, labels):
        return [
            dict(label)
            for label in labels
            for _copy in range(label['copies'])
        ]

    def _prepare_report_values(self, data):
        return {
            'labels': self._expand_labels(self._prepare_rendering_labels(data['labels'])),
            'label_template': data['label_template'],
        }

    def _organize_labels(self, labels, rows=1, columns=1):
        slots_per_page = rows * columns
        if not labels:
            return []

        organized_pages = []
        for page_start in range(0, len(labels), slots_per_page):
            page_labels = list(labels[page_start:page_start + slots_per_page])
            while len(page_labels) < slots_per_page:
                page_labels.append(self._prepare_invisible_label())
            organized_pages.append([
                page_labels[row_start:row_start + columns]
                for row_start in range(0, slots_per_page, columns)
            ])
        return organized_pages

    def _get_report_label_values(self, labels, rows, columns):
        label_pages = self._organize_labels(labels, rows=rows, columns=columns)
        return {
            'label_pages': label_pages,
            'page_numbers': len(label_pages),
        }


class ReportLabelPdf(models.AbstractModel):
    _name = 'report.product.report_product_label_pdf'
    _inherit = 'report.product.label.base'
    _description = 'Label PDF Report'

    def _get_report_values(self, docids, data):
        layout = data['layout']
        report_values = self._prepare_report_values(data)
        labels = report_values.pop('labels')
        report_values.update(self._get_report_label_values(labels, layout['rows'], layout['columns']))
        return report_values


class ReportLabelDymo(models.AbstractModel):
    _name = 'report.product.report_product_label_dymo'
    _inherit = 'report.product.label.base'
    _description = 'Label Dymo Report'

    def _get_report_values(self, docids, data):
        report_values = self._prepare_report_values(data)
        report_values['page_numbers'] = len(report_values['labels'])
        return report_values


class ReportLabelZpl(models.AbstractModel):
    _name = 'report.product.report_product_label_zpl'
    _inherit = 'report.product.label.base'
    _description = 'Label ZPL Report'

    def _get_report_values(self, docids, data):
        report_values = self._prepare_report_values(data)
        for label in report_values['labels']:
            label['barcode_value'] = markupsafe.Markup(label['barcode_value'])
            label['name'] = markupsafe.Markup(label['name'])
            label['reference'] = markupsafe.Markup(label['reference'])
        return report_values
