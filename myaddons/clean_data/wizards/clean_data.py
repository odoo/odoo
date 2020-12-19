# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class CleanData(models.TransientModel):
    _name = 'clean.data'
    _description = 'Clean Data'

    so_do = fields.Boolean("Sales Delivery Orders")
    po = fields.Boolean('Purchase')
    all_trans = fields.Boolean('All Transfers')
    inv_pymt = fields.Boolean('Invoicing, Payments')
    journals = fields.Boolean('All Journal Entries')
    cus_ven = fields.Boolean('Customers & Vendors')
    coa = fields.Boolean('Chart Of Accounts')
    pos = fields.Boolean('Point Of Sale')
    all_data = fields.Boolean('All Data')
    mrp = fields.Boolean('Manufacturing')
    
    def check_and_delete(self,table):
        sql = """SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND   table_name = '%s');""" % table
        self._cr.execute(sql)
        res = self._cr.dictfetchall()
        res = res and res[0] or {}
        if res.get('exists', False):
            sql = """delete from %s ;""" % table
            self._cr.execute(sql)
            
    def _clear_so_order(self):
        sq = "stock_quant"
        sml = "stock_move_line"
        sm = "stock_move"
        sp = "stock_picking"
        apr = "account_partial_reconcile"
        aml = "account_move_line"
        am = "account_move"
        sol = "sale_order_line"
        so = "sale_order"
        self.check_and_delete(sq)
        self.check_and_delete(sml)
        self.check_and_delete(sm)
        self.check_and_delete(sp)
        self.check_and_delete(apr)
        self.check_and_delete(aml)
        self.check_and_delete(am)
        self.check_and_delete(sol)
        self.check_and_delete(so)

    def _clear_po(self):
        sq = "stock_quant"
        sml = "stock_move_line"
        sm = "stock_move"
        sp = "stock_picking"
        apr = "account_partial_reconcile"
        aml = "account_move_line"
        am = "account_move"
        po = 'purchase_order'
        pol = 'purchase_order_line'
        self.check_and_delete(sq)
        self.check_and_delete(sml)
        self.check_and_delete(sm)
        self.check_and_delete(sp)
        self.check_and_delete(apr)
        self.check_and_delete(aml)
        self.check_and_delete(am)
        self.check_and_delete(pol)
        self.check_and_delete(po)

    def _clear_transfer(self):
        sp = "stock_picking"
        sml = "stock_move_line"
        sm = "stock_move"
        sq = "stock_quant"
        self.check_and_delete(sq)
        self.check_and_delete(sml)
        self.check_and_delete(sm)
        self.check_and_delete(sp)

    def _clear_inv_pymt(self):
        apr = "account_partial_reconcile"
        aml = "account_move_line"
        am = "account_move"
        ap = "account_payment"
        self.check_and_delete(apr)
        self.check_and_delete(aml)
        self.check_and_delete(am)
        self.check_and_delete(ap)

    def _clear_cus_ven(self):
        rp = "delete from res_partner where id not in (select partner_id from res_users union select " \
             "partner_id from res_company); "
        self._cr.execute(rp)

    def _clear_coa(self):
        at = "account_tax"
        absl = "account_bank_statement_line"
        abs = "account_bank_statement"
        ppm = "pos_payment_method"
        aj = "account_journal"
        coa = "account_account"
        self.check_and_delete(at)
        self.check_and_delete(absl)
        self.check_and_delete(abs)
        self.check_and_delete(ppm)
        self.check_and_delete(aj)
        self.check_and_delete(coa)

    def _clear_journal(self):
        aml = "account_move_line"
        am = "account_move"
        self.check_and_delete(aml)
        self.check_and_delete(am)
        
    @api.onchange('all_data')
    def all_true(self):
        for rec in self:
            if rec.all_data:
                rec.so_do = True
                rec.po = True
                rec.all_trans = True
                rec.inv_pymt = True
                rec.journals = True
                rec.cus_ven = True
                rec.coa = True
            else:
                rec.so_do = False
                rec.po = False
                rec.all_trans = False
                rec.inv_pymt = False
                rec.journals = False
                rec.cus_ven = False
                rec.coa = False

    def clean_data(self):
        for rec in self:
            if rec.all_data:
                self._clear_so_order()
                self._clear_po()
                self._clear_transfer()
                self._clear_inv_pymt()
                self._clear_cus_ven()
                self._clear_coa()
                self._clear_journal()
            if rec.so_do:
                self._clear_so_order()
            if rec.po:
                self._clear_po()
            if rec.all_trans:
                self._clear_transfer()
            if rec.inv_pymt:
                self._clear_inv_pymt()
            if rec.journals:
                self._clear_journal()
            if rec.cus_ven:
                self._clear_cus_ven()
            if rec.coa:
                self._clear_coa()