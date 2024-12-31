# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command

from odoo.addons.sale_pdf_quote_builder import utils


class SalePdfFormField(models.Model):
    _name = 'sale.pdf.form.field'
    _description = "Form fields of inside quotation documents."
    _order = 'name'

    name = fields.Char(
        string="Form Field Name",
        help="The form field name as written in the PDF.",
        readonly=True,
        required=True,
    )
    document_type = fields.Selection(
        string="Document Type",
        selection=[
            ('quotation_document', "Header/Footer"),
            ('product_document', "Product Document"),
        ],
        readonly=True,
        required=True,
    )
    path = fields.Char(
        string="Path",
        help="The path to follow to dynamically fill the form field. \n"
             "Leave empty to be able to customized it in the quotation form."
    )
    product_document_ids = fields.Many2many(
        string="Product Documents", comodel_name='product.document'
    )
    quotation_document_ids = fields.Many2many(
        string="Quotation Documents", comodel_name='quotation.document'
    )

    _unique_name_per_doc_type = models.Constraint(
        'UNIQUE(name, document_type)',
        'Form field name must be unique for a given document type.',
    )

    # === CONSTRAINT METHODS ===#

    @api.constrains('name')
    def _check_form_field_name_follows_pattern(self):
        """ Ensure the names only contains alphanumerics, hyphens and underscores.

        :return: None
        :raises: ValidationError if the names aren't alphanumerics, hyphens and underscores.
        """
        name_pattern = re.compile(r'^(\w|-)+$')
        for form_field in self:
            if not re.match(name_pattern, form_field.name):
                raise ValidationError(_(
                    "Invalid form field name %(field_name)s. It should only contain alphanumerics,"
                    " hyphens or underscores.",
                    field_name=form_field.name,
                ))
            if form_field.name.startswith('sol_id_'):
                raise ValidationError(_(
                    "Invalid form field name %(field_name)s. A form field name in a header or a"
                    " footer can not start with \"sol_id_\".",
                    field_name=form_field.name,
                ))

    @api.constrains('path')
    def _check_valid_and_existing_paths(self):
        """ Verify that the paths exist and are valid.

        :return: None
        :raises: ValidationError if at least one of the paths isn't valid.
        """
        name_pattern = re.compile(r'^(\w|-|\.)+$')
        for form_field in self.filtered('path'):
            if not re.match(name_pattern, form_field.path):
                raise ValidationError(_(
                    "Invalid path %(path)s. It should only contain alphanumerics, hyphens,"
                    " underscores or points.",
                    path=form_field.path,
                ))

            path = form_field.path.split('.')
            is_header_footer = form_field.document_type == 'quotation_document'
            Model = self.env['sale.order'] if is_header_footer else self.env['sale.order.line']
            for i in range(len(path)):
                field_name = path[i]
                if Model == []:
                    raise ValidationError(_(
                        "Please use only relational fields until the last value of your path."
                    ))
                if field_name not in Model._fields:
                    raise ValidationError(_(
                        "The field %(field_name)s doesn't exist on model %(model_name)s",
                        field_name=field_name,
                        model_name=Model._name
                    ))
                if i != len(path) - 1:
                    Model = Model[field_name]

    @api.constrains('document_type', 'product_document_ids', 'quotation_document_ids')
    def _check_document_type_and_document_linked_compatibility(self):
        for form_field in self:
            doc_type = form_field.document_type
            if doc_type == 'quotation_document' and form_field.product_document_ids:
                raise ValidationError(_(
                    "A form field set as used in product documents can't be linked to a quotation"
                    " document."
                ))
            elif doc_type == 'product_document' and form_field.quotation_document_ids:
                raise ValidationError(_(
                    "A form field set as used in quotation documents can't be linked to a product"
                    " document."
                ))

    # === BUSINESS METHODS ===#

    @api.model
    def _add_basic_mapped_form_fields(self):
        mapped_form_fields = {
            'quotation_document': {
                "amount_total": "amount_total",
                "amount_untaxed": "amount_untaxed",
                "client_order_ref": "client_order_ref",
                "delivery_date": "commitment_date",
                "order_date": "date_order",
                "name": "name",
                "partner_id__name": "partner_id.name",
                "user_id__email": "user_id.login",
                "user_id__name": "user_id.name",
                "validity_date": "validity_date",
            },
            'product_document': {
                "amount_total": "order_id.amount_total",
                "amount_untaxed": "order_id.amount_untaxed",
                "client_order_ref": "order_id.client_order_ref",
                "delivery_date": "order_id.commitment_date",
                "description": "name",
                "discount": "discount",
                "name": "order_id.name",
                "partner_id__name": "order_partner_id.name",
                "price_unit": "price_unit",
                "product_sale_price": "product_id.lst_price",
                "quantity": "product_uom_qty",
                "tax_excl_price": "price_subtotal",
                "tax_incl_price": "price_total",
                "taxes": "tax_ids",
                "uom": "product_uom_id.name",
                "user_id__name": "salesman_id.name",
                "validity_date": "order_id.validity_date",
            },
        }
        quote_doc = list(mapped_form_fields['quotation_document'])
        product_doc = list(mapped_form_fields['product_document'])
        existing_mapping = self.env['sale.pdf.form.field'].search([
            '|',
            '&', ('document_type', '=', 'quotation_document'), ('name', 'in', quote_doc),
            '&', ('document_type', '=', 'product_document'), ('name', 'in', product_doc)
        ])
        if existing_mapping:
            form_fields_to_add = {
                doc_type: {
                    name: path for name, path in mapped_form_fields[doc_type].items()
                    if not existing_mapping.filtered(
                        lambda ff: ff.document_type == doc_type and ff.name == name
                    )
                } for doc_type, mapping in mapped_form_fields.items()
            }
        else:
            form_fields_to_add = mapped_form_fields
        self.env['sale.pdf.form.field'].create([
            {'name': name, 'document_type': doc_type, 'path': path}
            for doc_type, mapping in form_fields_to_add.items()
            for name, path in mapping.items()
        ])

    @api.model
    def _cron_post_upgrade_assign_missing_form_fields(self):
        # Called post-upgrade as we can't access the files during the upgrade process
        product_documents = self.env['product.document'].search(
            [('attached_on_sale', '=', 'inside')]
        )
        quote_documents = self.env['quotation.document'].search([])
        self._create_or_update_form_fields_on_pdf_records(product_documents, 'product_document')
        self._create_or_update_form_fields_on_pdf_records(quote_documents, 'quotation_document')

    @api.model
    def _create_or_update_form_fields_on_pdf_records(self, records, doc_type):
        existing_form_fields = self.env['sale.pdf.form.field'].search(
            [('document_type', '=', doc_type)]
        )
        existing_form_fields_name = existing_form_fields.mapped('name')
        return_bin_size = self.env.context.get('bin_size')
        if return_bin_size:
            # guarantees that bin_size is always set to False
            records = records.with_context(bin_size=False)

        for document in records:
            if document.datas:
                form_fields = utils._get_form_fields_from_pdf(document.datas)
                for field in form_fields:
                    if field not in existing_form_fields_name:
                        document.form_field_ids = [
                            Command.create({
                                'name': field, 'document_type': doc_type
                            })
                        ]
                        existing_form_fields_name.append(field)
                        existing_form_fields += document.form_field_ids[-1]
                    else:
                        document.form_field_ids = [Command.link(existing_form_fields.filtered(
                            lambda form_field: form_field.name == field
                        ).id)]
