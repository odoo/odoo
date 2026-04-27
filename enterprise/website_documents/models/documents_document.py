# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models, fields, api
from odoo.exceptions import AccessError


class Document(models.Model):
    _name = 'documents.document'
    _inherit = ['documents.document']

    website_id = fields.Many2one(
        'website', ondelete='set null', compute='_compute_website_id', readonly=False, store=True,
        domain="['|', ('company_id', '=', company_id), ('company_id', 'in', context.get('allowed_company_ids'))]")

    @api.depends('website_id')
    def _compute_access_url(self):
        return super()._compute_access_url()

    @api.depends('company_id', 'company_id.website_id')
    @api.depends_context('allowed_company_ids')
    def _compute_website_id(self):
        for document in self.filtered(lambda d: not d.website_id or d.website_id.company_id != d.company_id):
            document.website_id = document.company_id.website_id or self.env.company.website_id

    @api.constrains('company_id', 'website_id')
    def _check_website_id(self):
        if self.env.is_superuser() or not self.env.companies:
            return
        invalid_docs = []
        for doc in self.filtered('website_id'):
            if (
                doc.company_id != doc.website_id.company_id
                and doc.website_id.company_id not in self.env.companies
            ):
                invalid_docs.append(doc.name)
        if invalid_docs:
            raise AccessError(_("You can't set this website for the following documents:\n- ") + '\n- '.join(invalid_docs))
