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

from odoo import models, api


class DoctorPaymentTemplate(models.AbstractModel):
    _name = 'report.flexipharmacy.pos_commission_report_template'
    _description = "Mixin model for applying to any object that wants to " \
                   "handle commissions"

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            docids = self.env['pos.doctor.commission.payment'].browse(self.env.context.get('active_ids'))
        return {
            'data': data['commission'],
            'doc_model': 'pos.doctor.commission.payment',
            'docs': docids,
            'docs_ids': docids.ids
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: