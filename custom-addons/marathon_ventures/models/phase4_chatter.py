# -*- coding: utf-8 -*-
"""Phase 4 — Add chatter (Send message / Log Note / Activity) to every mv.* model.

Each class extends the corresponding model to include the Odoo mail.thread and
mail.activity.mixin so the SF "Activity History" UX is reproduced on every record.
Views are extended via phase4_chatter_views.xml to render the <chatter/> widget.
"""
from odoo import models


class MvChatterAdvertiser(models.Model):
    _name = 'mv.advertiser'
    _inherit = ['mv.advertiser', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterAgencyDoubleCheck(models.Model):
    _name = 'mv.agency_double_check'
    _inherit = ['mv.agency_double_check', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterAgencyMatchErrorAccounts(models.Model):
    _name = 'mv.agency_match_error_accounts'
    _inherit = ['mv.agency_match_error_accounts', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterBrands(models.Model):
    _name = 'mv.brands'
    _inherit = ['mv.brands', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterBroadcastMonth(models.Model):
    _name = 'mv.broadcast_month'
    _inherit = ['mv.broadcast_month', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterBundlePricing(models.Model):
    _name = 'mv.bundle_pricing'
    _inherit = ['mv.bundle_pricing', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterCase(models.Model):
    _name = 'mv.case'
    _inherit = ['mv.case', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterCheck(models.Model):
    _name = 'mv.check'
    _inherit = ['mv.check', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterCheckDetail(models.Model):
    _name = 'mv.check_detail'
    _inherit = ['mv.check_detail', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterClearance(models.Model):
    _name = 'mv.clearance'
    _inherit = ['mv.clearance', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterClearanceList(models.Model):
    _name = 'mv.clearance_list'
    _inherit = ['mv.clearance_list', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterContract(models.Model):
    _name = 'mv.contract'
    _inherit = ['mv.contract', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterContracts(models.Model):
    _name = 'mv.contracts'
    _inherit = ['mv.contracts', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterCreditApplication(models.Model):
    _name = 'mv.credit_application'
    _inherit = ['mv.credit_application', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterCreditMonitoring(models.Model):
    _name = 'mv.credit_monitoring'
    _inherit = ['mv.credit_monitoring', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterCreditMonitoringInfo(models.Model):
    _name = 'mv.credit_monitoring_info'
    _inherit = ['mv.credit_monitoring_info', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterCurrentQuarterOverview(models.Model):
    _name = 'mv.current_quarter_overview'
    _inherit = ['mv.current_quarter_overview', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterCustomDebug(models.Model):
    _name = 'mv.custom_debug'
    _inherit = ['mv.custom_debug', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterDeal(models.Model):
    _name = 'mv.deal'
    _inherit = ['mv.deal', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterDisableRelatedScheduleEmail(models.Model):
    _name = 'mv.disable_related_schedule_email'
    _inherit = ['mv.disable_related_schedule_email', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterDoubleCheckedDeals(models.Model):
    _name = 'mv.double_checked_deals'
    _inherit = ['mv.double_checked_deals', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterHiatusExcluded(models.Model):
    _name = 'mv.hiatus_excluded'
    _inherit = ['mv.hiatus_excluded', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterIntacctEntity(models.Model):
    _name = 'mv.intacct_entity'
    _inherit = ['mv.intacct_entity', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterLoggerSettings(models.Model):
    _name = 'mv.logger_settings'
    _inherit = ['mv.logger_settings', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterMarket(models.Model):
    _name = 'mv.market'
    _inherit = ['mv.market', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterMassDealChange(models.Model):
    _name = 'mv.mass_deal_change'
    _inherit = ['mv.mass_deal_change', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterOpportunityLineItem(models.Model):
    _name = 'mv.opportunity_line_item'
    _inherit = ['mv.opportunity_line_item', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterOtherSalesDocument(models.Model):
    _name = 'mv.other_sales_document'
    _inherit = ['mv.other_sales_document', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterOtherSalesDocumentItem(models.Model):
    _name = 'mv.other_sales_document_item'
    _inherit = ['mv.other_sales_document_item', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterOtherSalesDocumentTotal(models.Model):
    _name = 'mv.other_sales_document_total'
    _inherit = ['mv.other_sales_document_total', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPiPayout(models.Model):
    _name = 'mv.pi_payout'
    _inherit = ['mv.pi_payout', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPoDetail(models.Model):
    _name = 'mv.po_detail'
    _inherit = ['mv.po_detail', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPrelogBatchNetworks(models.Model):
    _name = 'mv.prelog_batch_networks'
    _inherit = ['mv.prelog_batch_networks', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPrelogData(models.Model):
    _name = 'mv.prelog_data'
    _inherit = ['mv.prelog_data', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPrelogDataMirror(models.Model):
    _name = 'mv.prelog_data_mirror'
    _inherit = ['mv.prelog_data_mirror', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPrelogDataMirrors(models.Model):
    _name = 'mv.prelog_data_mirrors'
    _inherit = ['mv.prelog_data_mirrors', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPrelogFuzzyMatch(models.Model):
    _name = 'mv.prelog_fuzzy_match'
    _inherit = ['mv.prelog_fuzzy_match', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPrograms(models.Model):
    _name = 'mv.programs'
    _inherit = ['mv.programs', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPto(models.Model):
    _name = 'mv.pto'
    _inherit = ['mv.pto', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterPurchaseOrder(models.Model):
    _name = 'mv.purchase_order'
    _inherit = ['mv.purchase_order', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterRatingDetail(models.Model):
    _name = 'mv.rating_detail'
    _inherit = ['mv.rating_detail', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterRatingEstimates(models.Model):
    _name = 'mv.rating_estimates'
    _inherit = ['mv.rating_estimates', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterRatingHeader(models.Model):
    _name = 'mv.rating_header'
    _inherit = ['mv.rating_header', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterRatings(models.Model):
    _name = 'mv.ratings'
    _inherit = ['mv.ratings', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterRatingsCompiled(models.Model):
    _name = 'mv.ratings_compiled'
    _inherit = ['mv.ratings_compiled', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterRatingsCompilesDayparts(models.Model):
    _name = 'mv.ratings_compiles_dayparts'
    _inherit = ['mv.ratings_compiles_dayparts', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterRaycomMonthlyLineItem(models.Model):
    _name = 'mv.raycom_monthly_line_item'
    _inherit = ['mv.raycom_monthly_line_item', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterRequest(models.Model):
    _name = 'mv.request'
    _inherit = ['mv.request', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesInvoice(models.Model):
    _name = 'mv.sales_invoice'
    _inherit = ['mv.sales_invoice', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesInvoiceItem(models.Model):
    _name = 'mv.sales_invoice_item'
    _inherit = ['mv.sales_invoice_item', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesInvoicePayment(models.Model):
    _name = 'mv.sales_invoice_payment'
    _inherit = ['mv.sales_invoice_payment', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesInvoiceTotal(models.Model):
    _name = 'mv.sales_invoice_total'
    _inherit = ['mv.sales_invoice_total', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesOrder(models.Model):
    _name = 'mv.sales_order'
    _inherit = ['mv.sales_order', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesOrderItem(models.Model):
    _name = 'mv.sales_order_item'
    _inherit = ['mv.sales_order_item', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesOrderTotal(models.Model):
    _name = 'mv.sales_order_total'
    _inherit = ['mv.sales_order_total', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesPlan(models.Model):
    _name = 'mv.sales_plan'
    _inherit = ['mv.sales_plan', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesQuote(models.Model):
    _name = 'mv.sales_quote'
    _inherit = ['mv.sales_quote', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesQuoteItem(models.Model):
    _name = 'mv.sales_quote_item'
    _inherit = ['mv.sales_quote_item', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSalesQuoteTotal(models.Model):
    _name = 'mv.sales_quote_total'
    _inherit = ['mv.sales_quote_total', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSchedules(models.Model):
    _name = 'mv.schedules'
    _inherit = ['mv.schedules', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSfCreditMemo(models.Model):
    _name = 'mv.sf_credit_memo'
    _inherit = ['mv.sf_credit_memo', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSfCreditMemoDetail(models.Model):
    _name = 'mv.sf_credit_memo_detail'
    _inherit = ['mv.sf_credit_memo_detail', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSfCreditMemoOld(models.Model):
    _name = 'mv.sf_credit_memo_old'
    _inherit = ['mv.sf_credit_memo_old', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSfCreditReference(models.Model):
    _name = 'mv.sf_credit_reference'
    _inherit = ['mv.sf_credit_reference', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSplit(models.Model):
    _name = 'mv.split'
    _inherit = ['mv.split', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSpotData(models.Model):
    _name = 'mv.spot_data'
    _inherit = ['mv.spot_data', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSpotDataMirror(models.Model):
    _name = 'mv.spot_data_mirror'
    _inherit = ['mv.spot_data_mirror', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterSpotDataMirrors(models.Model):
    _name = 'mv.spot_data_mirrors'
    _inherit = ['mv.spot_data_mirrors', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterStation(models.Model):
    _name = 'mv.station'
    _inherit = ['mv.station', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterTape(models.Model):
    _name = 'mv.tape'
    _inherit = ['mv.tape', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterTimeAndExpense(models.Model):
    _name = 'mv.time_and_expense'
    _inherit = ['mv.time_and_expense', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterTimeAndExpenseDetail(models.Model):
    _name = 'mv.time_and_expense_detail'
    _inherit = ['mv.time_and_expense_detail', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterTraffic(models.Model):
    _name = 'mv.traffic'
    _inherit = ['mv.traffic', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterTrafficVideoAsset(models.Model):
    _name = 'mv.traffic_video_asset'
    _inherit = ['mv.traffic_video_asset', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterVideoFile(models.Model):
    _name = 'mv.video_file'
    _inherit = ['mv.video_file', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']

class MvChatterWorkingLog(models.Model):
    _name = 'mv.working_log'
    _inherit = ['mv.working_log', 'mail.thread', 'mail.activity.mixin', 'mv.save.button.mixin']
