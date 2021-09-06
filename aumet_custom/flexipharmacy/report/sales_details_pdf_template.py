# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import models, api, _


class SalesDetailsPdfTemplate(models.AbstractModel):
    _name = 'report.flexipharmacy.sales_details_pdf_template'
    _description = "pos report template"

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']. \
            _get_report_from_name('flexipharmacy.sales_details_pdf_template')
        return {'doc_ids': self.env['wizard.sales.details'].browse(data.get('ids')),
                'doc_model': report.model,
                'docs': self.env['wizard.sales.details'].browse(data['form']['user_ids']),
                'data': data}


class FrontSalesReportPdfTemplate(models.AbstractModel):
    _name = 'report.flexipharmacy.front_sales_report_pdf_template'
    _description = "aspl pos report sale report temp"

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('flexipharmacy.front_sales_report_pdf_template')
        return {'doc_ids': self.env['wizard.pos.x.report'].browse(data['ids']),
                'doc_model': report.model,
                'docs': self.env['pos.session'].browse(data['form']['session_ids']),
                'data': data}


class POSSalesReportPdfTemplate(models.AbstractModel):
    _name = 'report.flexipharmacy.pos_sales_report_pdf_template'
    _description = "POS Sales Report Template"

    @api.model
    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']. \
            _get_report_from_name('flexipharmacy.pos_sales_report_pdf_template')
        return {'doc_ids': self.env['wizard.pos.sale.report'].browse(data['ids']),
                'doc_model': report.model,
                'docs': self.env['pos.session'].browse(data['form']['session_ids']),
                'data': data}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
