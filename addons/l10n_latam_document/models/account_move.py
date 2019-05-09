# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
# from odoo.exceptions import UserError
from odoo.osv import expression


class AccountMove(models.Model):

    _inherit = "account.move"

    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        'Document Type',
        copy=False,
        auto_join=True,
        states={'posted': [('readonly', True)]},
        index=True,
    )
    l10n_latam_document_number = fields.Char(
        string='Document Number',
        copy=False,
        states={'posted': [('readonly', True)]},
        index=True,
    )
    display_name = fields.Char(
        compute='_compute_display_name',
        store=True,
        index=True,
    )

    @api.multi
    @api.depends(
        'l10n_latam_document_number',
        'name',
        'l10n_latam_document_type_id',
        'l10n_latam_document_type_id.doc_code_prefix',
    )
    def _compute_display_name(self):
        for rec in self:
            if rec.l10n_latam_document_number and rec.l10n_latam_document_type_id:
                display_name = (
                    rec.l10n_latam_document_type_id.doc_code_prefix or '') + \
                    rec.l10n_latam_document_number
            else:
                display_name = rec.l10n_latam_document_number or rec.name
            rec.display_name = display_name

    @api.multi
    @api.depends(
        'name', 'state',
        'l10n_latam_document_number', 'l10n_latam_document_type_id.doc_code_prefix')
    def name_get(self):
        """
        We overwrite default name_get function to use document_number if
        available
        """
        result = []
        for move in self:
            if move.state == 'draft':
                name = '* ' + str(move.id)
            else:
                name = move.display_name
            result.append((move.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """
        We add so it search by name and by document_number
        This is used, for eg, when we search a move on a m2o field
        We first search by display name that is computed by
        document_number (if exists) or name. We also search by name
        """
        args = args or []
        domain = []
        if name:
            domain = [
                '|',
                ('display_name', operator, name),
                # ('l10n_latam_document_number', operator, name),
                ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()
