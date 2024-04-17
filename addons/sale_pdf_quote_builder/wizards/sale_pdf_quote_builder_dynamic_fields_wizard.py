# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import json

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.sale_pdf_quote_builder.const import DEFAULT_FORM_FIELD_PATH_MAPPING


class SalePDFQuoteBuilderDynamicFieldsWizard(models.TransientModel):
    _name = 'sale.pdf.quote.builder.dynamic.fields.wizard'
    _description = "Sale PDF Quote Builder Dynamic Fields Configurator Wizard"

    current_form_fields = fields.Json()
    dynamic_fields_wizard_line_ids = fields.One2many(
        'sale.pdf.quote.builder.dynamic.fields.wizard.line', 'dynamic_fields_wizard_id'
    )

    @api.onchange('current_form_fields')
    def _get_wizard_lines(self):
        """ Add wizard lines containing existing mappings and form fields from the current document.
        """
        for wizard in self:
            wizard.dynamic_fields_wizard_line_ids = [Command.clear()]
            form_field_path_map = json.loads(self.env['ir.config_parameter'].sudo().get_param(
                'sale_pdf_quote_builder.form_field_path_mapping', DEFAULT_FORM_FIELD_PATH_MAPPING
            ))
            current_form_fields = json.loads(
                wizard.current_form_fields
            ) if wizard.current_form_fields else {}

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
            wizard.dynamic_fields_wizard_line_ids = [Command.create(vals) for vals in lines_vals]

    def validate_dynamic_fields_configuration(self):
        """ Save this mapping configuration in the config parameters. """
        for wizard in self:
            wizard_lines = wizard.dynamic_fields_wizard_line_ids
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

    dynamic_fields_wizard_id = fields.Many2one(
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
        for line in self.filtered(lambda line: line.path):
            if not re.match(name_pattern, line.path):
                raise ValidationError(_(
                    "Invalid path %(path)s. It should only contain alphanumerics, hyphens,"
                    " underscores or points.",
                    path=line.path,
                ))

            path = line.path.split('.')
            is_header_footer = line.document_type == 'header_footer'
            Model = self.env['sale.order'] if is_header_footer else self.env['sale.order.line']
            for elem in path:
                if not Model._fields.get(elem):
                    raise ValidationError(_(
                        "The field %(field_name)s doesn't exist on model %(model_name)s",
                        field_name=elem,
                        model_name=Model._name
                    ))
                if elem != path[-1]:
                    Model = Model.mapped(elem)
