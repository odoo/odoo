# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import demo

from .demo.account_demo import AccountChartTemplate
from .models.account_move import AccountMove
from .models.account_move_line import AccountMoveLine
from .models.account_tax import AccountTax
from .models.l10n_latam_document_type import L10n_LatamDocumentType
from .models.res_company import ResCompany
from .models.res_country import ResCountry
from .models.res_currency import ResCurrency
from .models.res_partner import ResPartner
from .models.res_partner_bank import ResBank
from .models.uom_uom import UomUom
