# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import models
from . import demo

from .demo.account_demo import AccountChartTemplate
from .models.account_journal import AccountJournal
from .models.account_move import AccountMove
from .models.account_tax import AccountTax
from .models.account_tax_group import AccountTaxGroup
from .models.l10n_ec_sri_payment import L10n_EcSriPayment
from .models.l10n_latam_document_type import L10n_LatamDocumentType
from .models.res_company import ResCompany
from .models.res_partner import ResPartner
