# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re

from odoo import _, api, models
from odoo.exceptions import ValidationError

_RUC_FORMATS = (
    # Persona jurídica: rollo/tomo-folio/imagen-asiento/ficha (Registro Público)
    re.compile(r'^\d{1,9}-\d{1,4}-\d{1,6}$'),
    # Persona natural: cédula (provincia-folio-asiento)
    re.compile(r'^\d{1,2}-\d{1,4}-\d{1,4}$'),
    # Persona natural extranjera (E), naturalizada (N), panameño extranjero (PE),
    # indígena (PI) o anterior a la vigencia del sistema (AV)
    re.compile(r'^(E|N|PE|PI|AV)-\d{1,2}-\d{1,4}-\d{1,4}$'),
    # Persona natural sin cédula de identidad personal (NT)
    re.compile(r'^NT[-\d]*$'),
)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.constrains('vat', 'country_id')
    def _check_pa_vat(self):
        for partner in self:
            vat = partner.vat or ''
            if partner.country_id.code != 'pa' or not vat:
                continue
            if not any(pattern.match(vat.strip().upper()) for pattern in _RUC_FORMATS):
                raise ValidationError(_(
                    "RUC inválido para %(name)s: el Registro Único de Contribuyentes en Panamá se "
                    "compone del número de inscripción en el Registro Público (rollo/tomo-folio/imagen-"
                    "asiento/ficha) para las personas jurídicas, o de la cédula de identidad personal "
                    "para las personas naturales (DGI). Ej.: 155066911-2-2019 o 8-741-2043.",
                    name=partner.display_name,
                ))
