##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ar_cuit = fields.Char(
        compute='_compute_l10n_ar_cuit',
    )
    l10n_ar_formated_cuit = fields.Char(
        compute='_compute_l10n_ar_formated_cuit',
    )
    l10n_ar_id_number = fields.Char(
        string='Identification Number',
    )
    l10n_ar_id_category_id = fields.Many2one(
        string="Identification Category",
        comodel_name='l10n_ar_id_category',
        index=True,
        auto_join=True,
    )

    @api.multi
    def cuit_required(self):
        """ Return the cuit number is this one is defined if not raise an
        UserError
        """
        self.ensure_one()
        if not self.l10n_ar_cuit:
            raise UserError(_(
                'No CUIT configured for partner [%i] %s') % (
                    self.id, self.name))
        return self.l10n_ar_cuit

    @api.depends('l10n_ar_cuit')
    def _compute_l10n_ar_formated_cuit(self):
        """ This will add some dash to the CUIT number in order to show in his
        natural format: {person_category}-{number}-{validation_number}
        """
        for rec in self:
            if not rec.l10n_ar_cuit:
                continue
            cuit = rec.l10n_ar_cuit
            rec.l10n_ar_formated_cuit = "{0}-{1}-{2}".format(
                cuit[0:2], cuit[2:10], cuit[10:])

    @api.depends('l10n_ar_id_number', 'l10n_ar_id_category_id')
    def _compute_l10n_ar_cuit(self):
        """ We add this computed field that returns cuit or nothing ig this one
        is not set for the partner. This validation can be also dony by calling
        cuit_required() method that returns the cuit nombre of error if this
        one is not found.
        """
        for rec in self:
            # If the partner is outside Argentina then we return the defined
            # country cuit defined by AFIP for that specific partner
            if rec.l10n_ar_id_category_id.afip_code != 80:
                country = rec.country_id
                if country and country.code != 'AR':
                    if rec.is_company:
                        rec.l10n_ar_cuit = country.l10n_ar_cuit_juridica
                    else:
                        rec.l10n_ar_cuit = country.l10n_ar_cuit_fisica
                continue
            if rec.l10n_ar_id_category_id.afip_code == 80:
                rec.l10n_ar_cuit = rec.l10n_ar_id_number

    @api.constrains('l10n_ar_id_number', 'l10n_ar_id_category_id')
    def check_vat(self):
        """ Update the the vat field using the information we have from
        l10n_ar_id_number and l10n_ar_id_category_id fields
        """
        for rec in self:
            if rec.l10n_ar_id_number and rec.l10n_ar_id_category_id and \
               rec.l10n_ar_id_category_id.afip_code == 80:
                rec.vat = 'AR' + rec.l10n_ar_id_number

    @api.constrains('l10n_ar_id_number', 'l10n_ar_id_category_id')
    def check_id_number_unique(self):
        """ Taking into account the company's general settings it will check
        that if the identification number we are trying to use is already set
        in another partner.
        """
        if not safe_eval(self.env['ir.config_parameter'].sudo().get_param(
                "l10n_ar_base.unique_id_numbers", 'False')):
            return True
        for rec in self:
            # We allow same number in related partners
            related_partners = rec.search([
                '|', ('id', 'parent_of', rec.id),
                ('id', 'child_of', rec.id)])
            same_id_numbers = rec.search([
                ('l10n_ar_id_number', '=', rec.l10n_ar_id_number),
                ('l10n_ar_id_category_id', '=', rec.l10n_ar_id_category_id.id),
                ('id', 'not in', related_partners.ids),
            ])
            if same_id_numbers:
                raise ValidationError(_(
                    'Identification number must be unique per Identification'
                    ' category!\nSame number is only allowed for partners with'
                    ' parent/child relation\n\n Already using this'
                    ' number: ') + ', '.join(same_id_numbers.mapped('name'))
                )

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100,
                     name_get_uid=None):
        """ We add the functionality to found partner by identification number
        """
        if not args:
            args = []
        # We used only this operarators in order to do not break the search.
        # For example: when searching like "Does not containt" in name field
        if name and operator in ('ilike', 'like', '=', '=like', '=ilike'):
            recs = self.search(
                [('l10n_ar_id_number', operator, name)] + args, limit=limit)
            if recs:
                return recs.name_get()
        return super(ResPartner, self)._name_search(
            name, args=args, operator=operator, limit=limit)
