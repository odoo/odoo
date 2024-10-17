# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import report
from . import wizard

from .models.account_move import AccountMove
from .models.account_move_line import AccountMoveLine
from .models.analytic import AccountAnalyticApplicability, AccountAnalyticLine
from .models.chart_template import AccountChartTemplate
from .models.crm_team import CrmTeam
from .models.payment_provider import PaymentProvider
from .models.payment_transaction import PaymentTransaction
from .models.product_document import ProductDocument
from .models.product_product import (
    ProductAttributeCustomValue, ProductPackaging,
    ProductProduct,
)
from .models.product_template import ProductTemplate
from .models.res_company import ResCompany
from .models.res_partner import ResPartner
from .models.sale_order import SaleOrder
from .models.sale_order_line import SaleOrderLine
from .models.utm_campaign import UtmCampaign
from .report.account_invoice_report import AccountInvoiceReport
from .report.sale_report import SaleReport
from .wizard.base_document_layout import BaseDocumentLayout
from .wizard.mass_cancel_orders import SaleMassCancelOrders
from .wizard.payment_link_wizard import PaymentLinkWizard
from .wizard.payment_provider_onboarding_wizard import SalePaymentProviderOnboardingWizard
from .wizard.res_config_settings import ResConfigSettings
from .wizard.sale_make_invoice_advance import SaleAdvancePaymentInv
from .wizard.sale_order_cancel import SaleOrderCancel
from .wizard.sale_order_discount import SaleOrderDiscount


def _post_init_hook(env):
    _synchronize_cron(env)
    _setup_property_downpayment_account(env)


def _synchronize_cron(env):
    send_invoice_cron = env.ref('sale.send_invoice_cron', raise_if_not_found=False)
    if send_invoice_cron:
        config = env['ir.config_parameter'].get_param('sale.automatic_invoice', False)
        send_invoice_cron.active = bool(config)


def _setup_property_downpayment_account(env):
    # Get companies that already have the property set
    ProductCategory = env['product.category']

    # Create property for companies without it
    for company in env.companies:
        if not company.chart_template or ProductCategory.with_company(company).search_count([('property_account_downpayment_categ_id', '!=', False)], limit=1):
            continue

        template_data = env['account.chart.template']._get_chart_template_data(company.chart_template).get('template_data')
        if template_data and template_data.get('property_account_downpayment_categ_id'):
            property_downpayment_account = env.ref(f'account.{company.id}_{template_data["property_account_downpayment_categ_id"]}', raise_if_not_found=False)
            if property_downpayment_account:
                env['ir.default'].set('product.category', 'property_account_downpayment_categ_id', property_downpayment_account.id, company_id=company.id)
