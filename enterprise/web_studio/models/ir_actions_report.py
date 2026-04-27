# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.osv import expression


class IrActionsReport(models.Model):
    _name = 'ir.actions.report'
    _inherit = ['studio.mixin', 'ir.actions.report']

    def _read_paper_format_measures(self, paperformat_fields=None):
        if paperformat_fields is None:
            paperformat_fields = ["margin_top", "margin_left", "margin_right", "print_page_height", "print_page_width", "header_spacing", "dpi", "disable_shrinking"]
        self.ensure_one()
        return self.get_paperformat().read(paperformat_fields)[0]

    @api.model
    def _render_qweb_html(self, report_ref, docids, data=None):
        if self._context.get("studio"):
            data = data or dict()
            data["studio"] = True
            data['report_type'] = 'pdf'
        return super(IrActionsReport, self)._render_qweb_html(report_ref, docids, data)

    def copy_report_and_template(self):
        new = self.copy()
        view = self.env['ir.ui.view'].search([
            ('type', '=', 'qweb'),
            ('key', '=', new.report_name),
        ], limit=1)
        view.ensure_one()
        new_view = view.with_context(lang=None).copy_qweb_template()
        copy_no = int(new_view.key.split('_copy_').pop())

        new.write({
            'xml_id': '%s_copy_%s' % (new.xml_id, copy_no),
            'name': '%s copy(%s)' % (new.name, copy_no),
            'report_name': '%s_copy_%s' % (new.report_name, copy_no),
            'report_file': new_view.key,  # TODO: are we sure about this?
        })

    def _get_rendering_context(self, report, docids, data):
        ctx = super()._get_rendering_context(report, docids, data)
        if self.env.context.get("studio") and not ctx.get("docs"):
            # TODO or not ?: user inputed values in data ?
            doc = self.env[report.model].new({})
            ctx["docs"] = doc
        return ctx

    @api.model
    def _get_rendering_context_model(self, report):
        # If the report is a copy of another report, and this report is using a custom model to render its html,
        # we must use the custom model of the original report.
        report_model_name = 'report.%s' % report.report_name
        report_model = self.env.get(report_model_name)

        if report_model is None:
            parts = report_model_name.split('_copy_')
            if any(not part.isdecimal() for part in parts[1:]):
                return report_model
            report_model_name = parts[0]
            report_model = self.env.get(report_model_name)

        return report_model

    def associated_view(self):
        action_data = super(IrActionsReport, self).associated_view()
        if action_data is not False:
            domain = expression.normalize_domain(action_data['domain'])

            view_name = self.report_name.split('.')[1].split('_copy_')[0]

            domain = expression.OR([
                domain,
                ['&', ('name', 'ilike', view_name), ('type', '=', 'qweb')]
            ])

            action_data['domain'] = domain
        return action_data
