# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ar_cuit = fields.Char(
        compute='_compute_l10n_ar_cuit',
        string="CUIT",
        help='Computed field that returns cuit or nothing if this one is not'
        ' set for the partner',
    )
    l10n_ar_formated_cuit = fields.Char(
        compute='_compute_l10n_ar_formated_cuit',
        string="Formated CUIT",
        help='Computed field that will convert the given cuit number to the'
        ' format {person_category:2}-{number:10}-{validation_number:1}',
    )
    l10n_ar_main_number = fields.Char(
        string='Main Identification Number',
        compute='_compute_l10n_ar_main_number',
        inverse='_inverse_l10n_ar_main_number',
        help='Techincal field used to return the identification number to use '
        'for this partner. Could be VAT Number or Identification Number '
        'depending on the Identification Type',
    )
    l10n_ar_id_number = fields.Char(
        string='Identification Number',
        help='Number that appears in the person/legal entity identification'
        ' document. Number should be expressed completely in integers',
    )
    l10n_ar_identification_type_id = fields.Many2one(
        string="Identification Type",
        comodel_name='l10n_ar.identification.type',
        index=True,
        auto_join=True,
        help='The type od identifications defined by AFIP that could identify'
        ' a person or a legal entity when trying to made operations',
    )
    l10n_ar_same_id_number_partner = fields.Html(
        string='Partner with same Identification Number',
        compute='_compute_l10n_ar_same_id_number_partner',
        store=False,
        help='Technical field used to show a warning when trying to create a '
        ' a partner with a identification number already used by another'
        ' partner. Parent/child partners could share identification number'
        ' so for this cases not warning will appears',
    )

    @api.onchange('l10n_ar_identification_type_id', 'l10n_ar_main_number')
    def _inverse_l10n_ar_main_number(self):
        for rec in self.filtered('l10n_ar_identification_type_id'):
            if rec.l10n_ar_identification_type_id.afip_code == 80:
                rec.vat = rec.l10n_ar_main_number and 'AR%s' % rec.l10n_ar_main_number
            else:
                rec.l10n_ar_id_number = rec.l10n_ar_main_number

    @api.depends('l10n_ar_id_number', 'vat', 'l10n_ar_identification_type_id')
    def _compute_l10n_ar_main_number(self):
        for rec in self.filtered('l10n_ar_identification_type_id'):
            if rec.l10n_ar_identification_type_id.afip_code == 80:
                rec.l10n_ar_main_number = rec.vat and rec.vat.replace('AR', '')
            else:
                rec.l10n_ar_main_number = rec.l10n_ar_id_number

    @api.depends('l10n_ar_id_number', 'l10n_ar_identification_type_id')
    def _compute_l10n_ar_same_id_number_partner(self):
        cuit_id_type = self.env.ref('l10n_ar_base.dt_CUIT')
        for partner in self:
            partner_id = partner.id
            partner_id_number = partner.l10n_ar_id_number
            partner_id_type = partner.l10n_ar_identification_type_id
            if partner_id_type != cuit_id_type:
                continue
            if isinstance(partner_id, models.NewId):
                # deal with onchange(), which is always called on a single
                # record
                partner_id = self._origin.id
            domain = [
                ('l10n_ar_id_number', '=', partner_id_number),
                ('l10n_ar_identification_type_id', '=', partner_id_type.id)]
            if partner_id:
                related_partners = partner.search([
                    '|', ('id', 'parent_of', partner_id),
                    ('id', 'child_of', partner_id)])
                domain += [('id', 'not in', related_partners.ids)]
            same_number_partner = self.env['res.partner'].search(
                domain, limit=1)
            partner.l10n_ar_same_id_number_partner = \
                "<a href='/web#id={}&model=res.partner' target='_blank'>{}"\
                "</a>".format(
                    same_number_partner.id, same_number_partner.name) \
                        if partner_id_number and partner_id_type and \
                            same_number_partner else False

    @api.multi
    def ensure_cuit(self):
        """ This method is a helper that returns the cuit number is this one is
        defined if not raise an UserError.

        CUIT is not mandatory field but for some Argentinian operations the
        cuit is required, for eg  validate an electronic invoice, build a
        report, etc.

        This method can be used to validate is the cuit is proper defined in
        the partner
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

    @api.depends('l10n_ar_id_number', 'l10n_ar_identification_type_id')
    def _compute_l10n_ar_cuit(self):
        """ We add this computed field that returns cuit or nothing ig this one
        is not set for the partner. This validation can be also done by calling
        ensure_cuit() method that returns the cuit or error if this one is not
        found.
        """
        for rec in self:
            # If the partner is outside Argentina then we return the defined
            # country cuit defined by AFIP for that specific partner
            if rec.l10n_ar_identification_type_id.afip_code != 80:
                country = rec.country_id
                if country and country.code != 'AR':
                    if rec.is_company:
                        rec.l10n_ar_cuit = country.l10n_ar_cuit_juridica
                    else:
                        rec.l10n_ar_cuit = country.l10n_ar_cuit_fisica
                continue
            if rec.l10n_ar_identification_type_id.afip_code == 80:
                rec.l10n_ar_cuit = rec.l10n_ar_id_number

    @api.constrains('parent_id', 'commercial_partner_id',
                    'l10n_ar_identification_type_id', 'l10n_ar_id_number')
    def check_cuit_commercial_partner(self):
        """ Can not set CUIT for non commercial partners
        """
        cuit_id_type = self.env.ref('l10n_ar_base.dt_CUIT')
        contacts_with_cuit = self.filtered(
            lambda x: x.l10n_ar_id_number and
            x.l10n_ar_identification_type_id == cuit_id_type and
            x.id != x.commercial_partner_id.id
        )
        if contacts_with_cuit:
            raise ValidationError(_(
                'Can not define CUIT for contacts, you can set cuit'
                ' to Commercial Entity. Check contacts: %s') % ', '.join(
                    contacts_with_cuit.mapped('name'))
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
