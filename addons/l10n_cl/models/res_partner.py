# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    country_id = fields.Many2one(
        'res.country',
        default=lambda self: self.env.ref('base.cl'))

    _sii_taxpayer_types = [
        ('1', 'IVA Afecto 1ra Categoría'),
        ('2', 'Emisor de Boletas 2da Categoría'),
        ('3', 'Consumidor Final'),
        ('4', 'Extranjero'),
    ]

    l10n_cl_sii_taxpayer_type = fields.Selection(
        _sii_taxpayer_types,
        'Taxpayer Types',
        index=True,
        default='1',
        help='1 - IVA Afecto (la mayoría de los casos)\n'
        '2 - Emisor Boletas (aplica solo para proveedores emisores de boleta)\n'
        '3 - Consumidor Final (se le emitirán siempre boletas)\n'
        '4 - Extranjero'
    )

    # TODO: change to a selection l10n_latam_identification_type (punto 2)
    l10n_latam_identification_type_id = fields.Many2one(
        string="Identification Type",
        comodel_name='l10n_latam.identification.type',
        index=True,
        auto_join=True,
        help='The type of identifications used in Chile that could identify'
             ' a physical or legal person',
    )
    l10n_cl_rut = fields.Char(
        compute='_compute_l10n_cl_rut',
        string="Invoicing RUT",
        help='Computed field that will convert the given rut number to often'
             ' local used format',
    )
    l10n_cl_rut_dv = fields.Char(
        compute='_compute_l10n_cl_rut',
        string="RUT's DV",
        help='Computed field that returns RUT or nothing if this one is not'
             ' set for the partner',
    )

    def _get_validation_module(self):
        self.ensure_one()
        if not self.country_id:
            return False, False
        elif self.l10n_latam_identification_type_id.name in ['RUT', 'RUN']:
            country_origin = 'cl'
        elif self.country_id.code != 'CL':
            country_origin = self.country_id.code.lower()
        else:
            return False, False
        try:
            country_validator = getattr(
                __import__('stdnum', fromlist=[country_origin]), country_origin)
        except AttributeError:
            # there is no validator for the selected country
            return False, False
        if 'vat' in dir(country_validator):
            return country_validator.vat, country_origin
        else:
            return False, False

    def l10n_cl_latamfication_validator(self):
        for rec in self.filtered('vat'):
            module = rec._get_validation_module()
            if not module[0]:
                continue
            try:
                module[0].validate(rec.vat)
            except module[0].InvalidChecksum:
                raise ValidationError(_('The validation digit is not valid.'))
            except module[0].InvalidLength:
                raise ValidationError(_('Invalid length.'))
            except module[0].InvalidFormat:
                raise ValidationError(_('Only numbers allowed.'))
            except Exception as error:
                raise ValidationError(repr(error))

    @api.constrains('vat', 'l10n_latam_identification_type_id')
    def check_vat(self):
        l10n_cl_partners = self.filtered('l10n_latam_identification_type_id')
        l10n_cl_partners.l10n_cl_latamfication_validator()
        return super(ResPartner, self - l10n_cl_partners).check_vat()

    @api.depends('vat', 'country_id', 'l10n_latam_identification_type_id')
    @api.onchange('vat', 'country_id', 'l10n_latam_identification_type_id')
    def _compute_l10n_cl_rut(self):
        for rec in self.filtered('vat'):
            module = rec._get_validation_module()
            if not module[0]:
                continue
            rec.l10n_cl_rut = module[0].format(rec.vat)
            if module[1] == 'cl':
                rec.l10n_cl_rut = rec.l10n_cl_rut.replace('.', '')
                rec.vat = rec.l10n_cl_rut
            else:
                rec.vat = module[0].format(rec.vat)
                rec.l10n_cl_rut = '55555555-5'
            rec.l10n_cl_rut_dv = rec.l10n_cl_rut[-1:]

    def validate_rut(self):
        self.ensure_one()
        if not self.l10n_cl_rut:
            raise UserError(_(
                'No RUT configured for partner [%i] %s') % (self.id, self.name))
        return self.l10n_cl_rut

    @api.onchange('country_id')
    def _adjust_identification_type(self):
        if self.country_id == self.env.ref('base.cl'):
            self.l10n_latam_identification_type_id = self.env.ref(
                'l10n_cl.it_RUT')
        else:
            self.l10n_latam_identification_type_id = self.env.ref(
                'l10n_latam_base.it_vat')
        self.vat = self.l10n_cl_rut = self.l10n_cl_rut_dv = False
