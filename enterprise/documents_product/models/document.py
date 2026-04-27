# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class Document(models.Model):
    _inherit = 'documents.document'

    product_template_id = fields.Many2one('product.template', string="Product", compute='_compute_product', search='_search_product_template_id')
    product_id = fields.Many2one('product.product', string="Product Variant", compute='_compute_product', search='_search_product_id')

    @api.depends('res_id', 'res_model')
    def _compute_product(self):
        ProductTemplate = self.env['product.template']
        Product = self.env['product.product']
        for document in self:
            document.product_template_id = document.res_model == 'product.template' and ProductTemplate.browse(document.res_id)
            document.product_id = document.res_model == 'product.product' and Product.browse(document.res_id)

    @api.model
    def _search_product_template_id(self, operator, value):
        return self._search_related_product_field(operator, value, self.env['product.template'])

    @api.model
    def _search_product_id(self, operator, value):
        return self._search_related_product_field(operator, value, self.env['product.product'])

    @api.model
    def _search_related_product_field(self, operator, value, Model):
        if operator in ('=', '!=') and isinstance(value, bool):
            if not value:
                operator = expression.TERM_OPERATORS_NEGATION[operator]
            return [("res_model", operator, Model._name)]
        elif operator in ('=', '!=', "in", "not in") and isinstance(value, (int, list)):
            return expression.AND([[("res_model", "=", Model._name)], [("res_id", operator, value)]])
        elif operator in ("ilike", "not ilike", "=", "!=") and isinstance(value, str):
            query_model = Model._search([(Model._rec_name, operator, value)])
            query_doc = self._search([('res_model', '=', Model._name), ('res_id', 'in', query_model)])
            return [("id", "in", query_doc)]
        raise ValidationError(_("Invalid %s search", self.env['ir.model']._get(Model._name).name))

    def create_product_template(self):
        # JUC: WTF? A single product for many documents, and the created
        #      product has the image of the first document?!

        product = self.env['product.template'].create({
            'name': _('Product created from Documents')
        })

        for document in self:
            if ((document.res_model or document.res_id)
                and document.res_model != 'documents.document'
            ):
                att_copy = document.attachment_id.with_context(no_document=True).copy()
                document = document.copy({'attachment_id': att_copy.id})
            document.write({
                'res_model': product._name,
                'res_id': product.id,
            })
            is_image = (document.mimetype or '').partition('/')[0] == 'image'
            if is_image and not product.image_1920:
                product.write({'image_1920': document.datas})

        view_id = product.get_formview_id()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.template',
            'name': "New product template",
            'context': self.env.context,
            'view_mode': 'form',
            'views': [(view_id, "form")],
            'res_id': product.id,
            'view_id': view_id,
        }

    def write(self, vals):
        """Sync product.document attachment when a document sharing a common
        attachment with a product/template is updated."""
        documents_for_products = self.filtered(
            lambda d: d.res_model in ('product.template', 'product.product')
            and d.attachment_id
        )
        if 'attachment_id' not in vals or not documents_for_products:
            return super().write(vals)
        document_by_old_attachment = documents_for_products.grouped('attachment_id')
        res = super().write(vals)
        product_docs = self.env['product.document'].search([
            ('ir_attachment_id', 'in', [a.id for a in document_by_old_attachment])
        ])
        for product_doc in product_docs:
            updated_related_document = document_by_old_attachment[product_doc.ir_attachment_id]
            product_doc.ir_attachment_id = updated_related_document.attachment_id
        return res
