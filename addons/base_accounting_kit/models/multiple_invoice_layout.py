# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models
from odoo.modules import get_resource_path

try:
    import sass as libsass
except ImportError:
    libsass = None


class MultipleInvoiceLayout(models.TransientModel):
    """
    Customise the invoice copy document layout and display a live preview
    """
    _name = 'multiple.invoice.layout'
    _description = 'Multiple Invoice Document Layout'

    def _get_default_journal(self):
        """The default function to return the journal for the invoice"""
        return self.env['account.journal'].search(
            [('id', '=', self.env.context.get('active_id'))]).id

    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, required=True)
    layout = fields.Char(related="company_id.external_report_layout_id.key")
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 required=True, default=_get_default_journal)
    multiple_invoice_type = fields.Selection(
        related='journal_id.multiple_invoice_type', readonly=False,
        required=True)
    text_position = fields.Selection(related='journal_id.text_position',
                                     readonly=False, required=True,
                                     default='header')
    body_text_position = fields.Selection(
        related='journal_id.body_text_position',
        readonly=False)
    text_align = fields.Selection(
        related='journal_id.text_align',
        readonly=False)
    preview = fields.Html(compute='_compute_preview',
                          sanitize=False,
                          sanitize_tags=False,
                          sanitize_attributes=False,
                          sanitize_style=False,
                          sanitize_form=False,
                          strip_style=False,
                          strip_classes=False)

    @api.depends('multiple_invoice_type', 'text_position', 'body_text_position',
                 'text_align')
    def _compute_preview(self):
        """ compute a qweb based preview to display on the wizard """

        styles = self._get_asset_style()

        for wizard in self:
            if wizard.company_id:
                preview_css = self._get_css_for_preview(styles, wizard.id)
                layout = self._get_layout_for_preview()
                ir_ui_view = wizard.env['ir.ui.view']
                wizard.preview = ir_ui_view._render_template(
                    'base_accounting_kit.multiple_invoice_wizard_preview',
                    {'company': wizard.company_id, 'preview_css': preview_css,
                     'layout': layout,
                     'mi_type': self.multiple_invoice_type,
                     'txt_position': self.text_position,
                     'body_txt_position': self.body_text_position,
                     'txt_align': self.text_align,
                     'mi': self.env.ref(
                         'base_accounting_kit.multiple_invoice_sample_name')
                     })
            else:
                wizard.preview = False

    def _get_asset_style(self):
        """Used to set the asset style"""
        company_styles = self.env['ir.qweb']._render(
            'web.styles_company_report', {
                'company_ids': self.company_id,
            }, raise_if_not_found=False)
        return company_styles

    @api.model
    def _get_css_for_preview(self, scss, new_id):
        """
        Compile the scss into css.
        """
        css_code = self._compile_scss(scss)
        return css_code

    @api.model
    def _compile_scss(self, scss_source):
        """
        This code will compile valid scss into css.
        Parameters are the same from odoo/addons/base/models/assetsbundle.py
        Simply copied and adapted slightly
        """

        # No scss ? still valid, returns empty css
        if not scss_source.strip():
            return ""

        precision = 8
        output_style = 'expanded'
        bootstrap_path = get_resource_path('web', 'static', 'lib', 'bootstrap',
                                           'scss')
        try:
            return libsass.compile(
                string=scss_source,
                include_paths=[
                    bootstrap_path,
                ],
                output_style=output_style,
                precision=precision,
            )
        except libsass.CompileError as e:
            raise libsass.CompileError(e.args[0])

    def _get_layout_for_preview(self):
        """Returns the layout Preview for the accounting module"""
        if self.layout == 'web.external_layout_boxed':
            new_layout = 'base_accounting_kit.boxed'

        elif self.layout == 'web.external_layout_bold':
            new_layout = 'base_accounting_kit.bold'

        elif self.layout == 'web.external_layout_striped':
            new_layout = 'base_accounting_kit.striped'

        else:
            new_layout = 'base_accounting_kit.standard'

        return new_layout

    def document_layout_save(self):
        """meant to be overridden document_layout_save"""
        return self.env.context.get('report_action') or {
            'type': 'ir.actions.act_window_close'}
