# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import misc
from odoo.tools.translate import _


L10N_CL_SII_REGIONAL_OFFICES_ITEMS = [
    ('ur_Anc', 'Ancud'),
    ('ur_Ang', 'Angol'),
    ('ur_Ant', 'Antofagasta'),
    ('ur_Ari', 'Arica y Parinacota'),
    ('ur_Ays', 'Aysén'),
    ('ur_Buin', 'Buin'),
    ('ur_Cal', 'Calama'),
    ('ur_Cas', 'Castro'),
    ('ur_Cau', 'Cauquenes'),
    ('ur_Cha', 'Chaitén'),
    ('ur_Chn', 'Chañaral'),
    ('ur_ChC', 'Chile Chico'),
    ('ur_Chi', 'Chillán'),
    ('ur_Coc', 'Cochrane'),
    ('ur_Cop', 'Concepción '),
    ('ur_Cos', 'Constitución'),
    ('ur_Coo', 'Copiapo'),
    ('ur_Coq', 'Coquimbo'),
    ('ur_Coy', 'Coyhaique'),
    ('ur_Cur', 'Curicó'),
    ('ur_Ill', 'Illapel'),
    ('ur_Iqu', 'Iquique'),
    ('ur_LaF', 'La Florida'),
    ('ur_LaL', 'La Ligua'),
    ('ur_LaS', 'La Serena'),
    ('ur_LaU', 'La Unión'),
    ('ur_Lan', 'Lanco'),
    ('ur_Leb', 'Lebu'),
    ('ur_Lin', 'Linares'),
    ('ur_Lod', 'Los Andes'),
    ('ur_Log', 'Los Ángeles'),
    ('ur_LosRios', 'Los Ríos'),
    ('ur_Nunoa', 'Ñuñoa'),
    ('ur_Maipu', 'Maipu'),
    ('ur_Melipilla', 'Melipilla'),
    ('ur_Oso', 'Osorno'),
    ('ur_Ova', 'Ovalle'),
    ('ur_Pan', 'Panguipulli'),
    ('ur_Par', 'Parral'),
    ('ur_Pic', 'Pichilemu'),
    ('ur_Por', 'Porvenir'),
    ('ur_PuM', 'Puerto Montt'),
    ('ur_PuN', 'Puerto Natales'),
    ('ur_PuV', 'Puerto Varas'),
    ('ur_PuA', 'Punta Arenas'),
    ('ur_Qui', 'Quillota'),
    ('ur_Ran', 'Rancagua'),
    ('ur_SaA', 'San Antonio'),
    ('ur_SanBernardo', 'San Bernardo'),
    ('ur_Sar', 'San Carlos'),
    ('ur_SaF', 'San Felipe'),
    ('ur_SaD', 'San Fernando'),
    ('ur_SaV', 'San Vicente de Tagua Tagua'),
    ('ur_SaZ', 'Santa Cruz'),
    ('ur_SaC', 'Santiago Centro'),
    ('ur_SaN', 'Santiago Norte'),
    ('ur_SaO', 'Santiago Oriente'),
    ('ur_SaP', 'Santiago Poniente'),
    ('ur_SaS', 'Santiago Sur'),
    ('ur_TaT', 'Tal-Tal'),
    ('ur_Tac', 'Talca'),
    ('ur_Tah', 'Talcahuano'),
    ('ur_Tem', 'Temuco'),
    ('ur_Toc', 'Tocopilla'),
    ('ur_Vld', 'Valdivia'),
    ('ur_Val', 'Vallenar'),
    ('ur_Vlp', 'Valparaíso'),
    ('ur_Vic', 'Victoria'),
    ('ur_ViA', 'Villa Alemana'),
    ('ur_ViR', 'Villarrica'),
    ('ur_ViM', 'Viña del Mar'),
]

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_cl_dte_email = fields.Char('DTE Email', related='partner_id.l10n_cl_dte_email', readonly=False)
    l10n_cl_dte_service_provider = fields.Selection([
        ('SIITEST', 'SII - Test'),
        ('SII', 'SII - Production'),
        ('SIIDEMO', 'SII - Demo Mode'),
    ], 'DTE Service Provider',
        help="Please select your company service provider for DTE service.")
    l10n_cl_dte_resolution_number = fields.Char(
        'SII Exempt Resolution Number',
        help='This value must be provided and must appear in your pdf or printed tribute document, under the '
             'electronic stamp to be legally valid.')
    l10n_cl_dte_resolution_date = fields.Date('SII Exempt Resolution Date')
    l10n_cl_sii_regional_office = fields.Selection(
        L10N_CL_SII_REGIONAL_OFFICES_ITEMS, translate=False, string='SII Regional Office')
    l10n_cl_company_activity_ids = fields.Many2many('l10n_cl.company.activities', string='Activities Names',
        help='Please select the SII registered economic activities codes for the company', readonly=False)
    l10n_cl_sii_taxpayer_type = fields.Selection(
        related='partner_id.l10n_cl_sii_taxpayer_type', index=True, readonly=False,
        help='1 - VAT Affected (1st Category) (Most of the cases)\n'
             '2 - Fees Receipt Issuer (Applies to suppliers who issue fees receipt)\n'
             '3 - End consumer (only receipts)\n'
             '4 - Foreigner')
    l10n_cl_certificate_ids = fields.One2many(
        'l10n_cl.certificate', 'company_id', string='Certificates (CL)')
    l10n_cl_is_there_shared_certificate = fields.Boolean('Is There Shared Certificate?', compute='_compute_is_there_shared_cert')

    def _prepare_cl_demo_objects(self):
        for c in self:
            if c.l10n_cl_dte_service_provider == 'SIIDEMO':
                c._create_demo_caf_files()
                sales_journals = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(c),
                    ('type', '=', 'sale'), ('l10n_latam_use_documents', '=', True),
                ])
                for sj in sales_journals:
                    sj.l10n_cl_point_of_sale_type = 'online'

    def _create_demo_caf_files(self, enabled_dte_documents=False):
        self.ensure_one()
        if not self.vat:
            raise UserError(_('To create demo CAF files, you must define the company VAT first.'))
        caf_file_template = misc.file_open('l10n_cl_edi/tests/template/caf_file_template.xml').read()
        today_string_date = fields.Date.to_string(fields.Date.context_today(
            self.with_context(tz='America/Santiago')))
        caf_file_template = caf_file_template. \
            replace('76201224-3', self.vat). \
            replace('Blanco Martin Asociados EIRL', self.name). \
            replace('<D>001</D><H>100</H>', '<D>1</D><H>999999</H>'). \
            replace('<IDK>100</IDK>', '<IDK>999999</IDK>'). \
            replace('2019-10-22', today_string_date)
        if not enabled_dte_documents:
            enabled_dte_documents = self.env['l10n_latam.document.type'].search(
                ['|', ('code', 'in', [52, 110, 111, 112]), ('l10n_cl_active', '=', True),
                 ('country_id.code', '=', 'CL')])
        existing_caf_files = self.env['l10n_cl.dte.caf'].search(
            [('company_id', '=', self.id)]).mapped('l10n_latam_document_type_id.code')
        for dte_caf in enabled_dte_documents:
            if dte_caf.code in existing_caf_files:
                continue
            caf_file = caf_file_template.replace('<TD></TD>', '<TD>%s</TD>' % dte_caf.code)
            self.env['l10n_cl.dte.caf'].sudo().create({
                'filename': ('FoliosSII%s%s%sDEMO.xml' % (self.vat, today_string_date, dte_caf.code)).replace('-', ''),
                'caf_file': base64.b64encode(caf_file.encode('utf-8')),
                'l10n_latam_document_type_id': dte_caf.id,
                'status': 'in_use',
                'company_id': self.id,
            })

    def _get_digital_signature(self, user_id=None):
        """
        This method looks for a digital signature that could be used to sign invoices for the current company.
        If the digital signature is intended to be used exclusively by a single user, it will have that user_id
        otherwise, if the user is false, it is understood that the owner of the signature (which is always
        a natural person) shares it with the rest of the users for that company.
        """
        if user_id is not None:
            user_certificates = self.l10n_cl_certificate_ids.filtered(
                lambda x: x._is_valid_certificate() and x.user_id.id == user_id and
                          x.company_id.id == self.id)
            if user_certificates:
                return user_certificates[0]
        shared_certificates = self.l10n_cl_certificate_ids.filtered(
            lambda x: x._is_valid_certificate() and not x.user_id and x.company_id.id == self.id)
        if not shared_certificates:
            raise UserError(_('There is not a valid certificate for the company: %s') % self.name)
        return shared_certificates[0]

    @api.depends('l10n_cl_dte_service_provider')
    def _compute_is_there_shared_cert(self):
        cl_certificate = self.env['l10n_cl.certificate']
        for company in self:
            domain = [('user_id', '=', False), ('company_id', '=', company.id)]
            company.l10n_cl_is_there_shared_certificate = cl_certificate.search(domain, limit=1)
