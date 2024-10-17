# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models

from .models.l10n_latam_identification_type import L10n_LatamIdentificationType
from .models.res_company import ResCompany
from .models.res_partner import ResPartner


def _set_default_identification_type(env):
    env.cr.execute(
        """
            UPDATE res_partner
               SET l10n_latam_identification_type_id = %s
        """,
        [env.ref('l10n_latam_base.it_vat').id]
    )
