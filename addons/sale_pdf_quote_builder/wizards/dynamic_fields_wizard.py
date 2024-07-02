# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import re

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.sale_pdf_quote_builder import utils
from odoo.addons.sale_pdf_quote_builder.const import DEFAULT_FORM_FIELD_PATH_MAPPING


class SalePDFQuoteBuilderDynamicFieldsWizard(models.TransientModel):
    _name = 'sale.pdf.quote.builder.dynamic.fields.wizard'
    _description = "Sale PDF Quote Builder Dynamic Fields Configurator Wizard"

    @api.model
    def _default_wizard_line_ids(self):
        res_id = self.env.context.get('active_id')
        res_model = self.env.context.get('active_model')
        if res_model == 'res.config.settings':
            # Avoid relying on wizard records
            document = self.env.company
        else:
            document = self.env[res_model].browse(res_id)
        if res_model == 'product.document':
            valid_form_fields = utils._get_form_fields_from_pdf(document.datas)
            current_form_fields = {'product_document': list(valid_form_fields)}
        else:
            valid_form_fields = set()
            if document.sale_header:
                valid_form_fields.update(utils._get_form_fields_from_pdf(document.sale_header))
            if document.sale_footer:
                valid_form_fields.update(utils._get_form_fields_from_pdf(document.sale_footer))
            current_form_fields = {'header_footer': list(valid_form_fields)}
        return self._get_wizard_lines(current_form_fields)

    def _get_wizard_lines(self, current_form_fields):
        """ Add wizard lines containing existing mappings and form fields from the current document.
        """
        form_field_path_map = json.loads(self.env['ir.config_parameter'].sudo().get_param(
            'sale_pdf_quote_builder.form_field_path_mapping', DEFAULT_FORM_FIELD_PATH_MAPPING
        ))

        # Get the form fields not yet in the config parameters
        lines_vals = []
        for doc_type, form_fields in current_form_fields.items():
            for form_field in form_fields:
                if form_field not in form_field_path_map[doc_type]:
                    lines_vals.extend([
                        {'document_type': doc_type, 'form_field': form_field, 'path': ''}
                    ])
        # Add existing values from the config parameter
        lines_vals.extend([
            {'document_type': doc_type, 'form_field': form_field, 'path': path}
            for doc_type, mapping in form_field_path_map.items()
            for form_field, path in mapping.items()
        ])
        # Create the wizard lines
        return [Command.create(vals) for vals in lines_vals]

    wizard_line_ids = fields.One2many(
        comodel_name='sale.pdf.quote.builder.dynamic.fields.wizard.line',
        inverse_name='wizard_id',
        default=_default_wizard_line_ids,
    )

    def save_configuration(self):
        """ Save this mapping configuration in the config parameters. """
        for wizard in self:
            wizard_lines = wizard.wizard_line_ids
            so_wiz_line = wizard_lines.filtered(lambda line: line.document_type == 'header_footer')
            sol_wiz_line = wizard_lines - so_wiz_line
            new_mapping = {
                'header_footer': {line.form_field: line.path or '' for line in so_wiz_line},
                'product_document': {line.form_field: line.path or '' for line in sol_wiz_line},
            }

            self.env['ir.config_parameter'].set_param(
                'sale_pdf_quote_builder.form_field_path_mapping', json.dumps(new_mapping)
            )


class SalePDFQuoteBuilderDynamicFieldsWizardLine(models.TransientModel):
    _name = 'sale.pdf.quote.builder.dynamic.fields.wizard.line'
    _description = "SalePdfQuoteBuilderDynamicFieldsWizardLine transient representation"

    wizard_id = fields.Many2one(
        'sale.pdf.quote.builder.dynamic.fields.wizard', required=True, ondelete='cascade'
    )
    document_type = fields.Selection(
        string="Document Type",
        selection=[('header_footer', "Header/Footer"), ('product_document', "Product Document")],
        default='header_footer',
        required=True,
    )
    form_field = fields.Char(
        string="Form Field", help="Form Field Name as seen in the PF form", required=True,
    )
    path = fields.Char(default='', help="Odoo path to get the expected value to fill the PDF.")

    @api.constrains('form_field')
    def _check_form_field_name_follows_pattern(self):
        """ Ensure the paths only contains alphanumerics, hyphens and underscores.

        :return: None
        :raises: ValidationError if the names aren't alphanumerics, hyphens and underscores.
        """
        name_pattern = re.compile(r'^(\w|-)+$')
        for line in self:
            if not re.match(name_pattern, line.form_field):
                raise ValidationError(_(
                    "Invalid form field name %(field_name)s. It should only contain alphanumerics,"
                    " hyphens or underscores.",
                    field_name=line.form_field,
                ))
            if line.document_type == 'header_footer' and line.form_field.startswith('sol_id_'):
                raise ValidationError(_(
                    "Invalid form field name %(field_name)s. A form field name in a header or a"
                    " footer can not start with \"sol_id_\".",
                    field_name=line.form_field,
                ))

    @api.constrains('path')
    def _check_valid_and_existing_paths(self):
        """ Verify that the paths exist and are valid.

        :return: None
        :raises: ValidationError if at least one of the paths isn't valid.
        """
        name_pattern = re.compile(r'^(\w|-|\.)+$')
        for line in self.filtered('path'):
            if not re.match(name_pattern, line.path):
                raise ValidationError(_(
                    "Invalid path %(path)s. It should only contain alphanumerics, hyphens,"
                    " underscores or points.",
                    path=line.path,
                ))

            path = line.path.split('.')
            is_header_footer = line.document_type == 'header_footer'
            Model = self.env['sale.order'] if is_header_footer else self.env['sale.order.line']
            for field_name in path:
                if field_name not in Model._fields:
                    raise ValidationError(_(
                        "The field %(field_name)s doesn't exist on model %(model_name)s",
                        field_name=field_name,
                        model_name=Model._name
                    ))
                if field_name != path[-1]:
                    Model = Model.mapped(field_name)
