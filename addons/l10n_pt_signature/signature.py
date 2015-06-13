#! -*- encoding: utf-8 -*-
##############################################################################

import os, datetime
from openerp import models, api, fields, _
#, fields
# from tools.translate import _

key = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQC3aFgWXwdt4OlLmWkwXBh/lRTSSZoyieKKELQKm1mwr7W24c11
KQa+kFiWEzETrVm8zhJgbzczUNsUzEyKSGzgNTNzO3yIbJhGkUREUEpPG+n0nwm6
NDETsXiUMwL7TPwRudy8QCXYa1q0dmDT0HF4Q0SLQOkfl3wPQpwf/cDp/QIDAQAB
AoGACMBCy7Z3DUgY+ZF1UmhihtvfJXV7lQO9Omc3n/Xvnp2Tpwk5G2j8uGT8xRRf
WBgCWx7eA5nq4VjvSxvAXyy7fRY4CuGNGqIVX7TqHZdABmU/BIIBpobxPa8G6oBC
kqL+GW1+RK4mtA1WxQvGEe1fEEfrMTmozEH6GPPRGhq1FYUCQQD/P618VhgS7fkU
JUfzdDiRCVE7X78lpFUVXz2i9G2tha1eR05DuqgF70r71AKq+gAvxKVQCLG2QtxQ
RMnxgfOnAkEAt/KJR5/qUVBt4nzYuGVNsvVz53U22oA/21Vivx/q59rkGsT7AnIM
nddIMitrRFTeFavZbWU5qqun3FB3OEZ5uwJAL8vMwKuedmz5ZzxT7NKmhQIpo+SZ
9oJ/LDFZaVo773JItI7FqQkazYGxmNZqaXnG7yrzibkXDfoXJzC6X+7loQJAWVHl
BSmKrydd5D95QLi4LPDw8fBBzYG/ADMK+wF1oFXys2j49awJok9aGDprIMgQ+vby
YiNoCA7IOLu92E6oZwJBAI1GeKxf5Yg9allbxhU4PW856EM/pWWTd6M7PpY0AZ/e
374e0apMgrootasdNl+LugkcQ/GYzYnVXw7sgNSH72Q=
-----END RSA PRIVATE KEY-----"""


priv_key = 'keys/demoprivatekey.pem'
try:
    a=open(priv_key)
    a.close()
except IOError:
    os.mkdir('keys')
    k = open(priv_key, 'w')
    k.write(key)
    k.close()
hash_control = 1

class account_invoice(models.Model):
    _name = 'account.invoice'
    _inherit = 'account.invoice'

    def get_hash(self, inv_id):
        """Gets the previous invoice of the same type and journal, and returns it's signature to be included in next invoice's string to sign
        """
        res = {}
        #invoice_obj=self.pool.get('account.invoice')
        invoice = self.browse(inv_id)
        self._cr.execute("SELECT hash FROM account_invoice inv \
                    WHERE internal_number = (\
                        SELECT MAX( internal_number) FROM account_invoice \
                        WHERE journal_id = " + str(invoice.journal_id.id)+" \
                            AND internal_number < '"+ invoice.internal_number +"'\
                            AND period_id in (SELECT id FROM account_period WHERE fiscalyear_id = "+str(invoice.period_id.fiscalyear_id.id)+") \
                            AND state in ('open', 'paid', 'cancel') )" )
        res = self._cr.fetchone()
        if res is None:
            return ''
        else :
            return res[0]

    _defaults = {
        'hash_control': lambda *a: hash_control
        }

    def action_signature(self):
        """Write hash and system_entry_date """
        # duvida: usar esta accao ou adicionar action_sign a incluir num workflow redesenhado, que substitua o original ????

        for invoice in self:
            # if invoice.state in ('open', 'paid', 'cancel') # not necessary, wkf determines properlly when this action is called
            # continues when it is not necessary to sign the invoices
            if (invoice.type in ('out_refund','out_invoice') and invoice.journal_id.self_billing) or (invoice.type in ('in_refund','in_invoice') and not invoice.journal_id.self_billing ) :
                continue
            inv_date = str(invoice.date_invoice)
            now = invoice.system_entry_date or datetime.datetime.now()
            try:
                invoiceNo = str(invoice.journal_id.saft_inv_type+' '+invoice.number)
            except TypeError:
                raise osv.except_osv(_('Error !'), _("Please set the doc type at Journal's SAFT parameters!"))
                return
            gross_total = self.grosstotal(invoice.id)
            prev_hash = self.get_hash(invoice.id)

            message = inv_date + ';' + str(now)[:19].replace(' ', 'T') + ';' + invoiceNo + ';' + gross_total + ';' + prev_hash
            
            signature = os.popen('echo -n "' + message + '" | openssl dgst -sha1 -sign ' + priv_key + ' | openssl enc -base64 -A', "r").read()
            self._cr.execute("UPDATE account_invoice SET hash = '%s' WHERE id = %d" % (signature, invoice.id))
            
            if not invoice.system_entry_date:
                self._cr.execute("UPDATE account_invoice SET system_entry_date = '%s' WHERE id = %d" %(now, invoice.id) )
        return True

    def action_cancel(self, *args):
        account_move_obj = self.pool.get('account.move')
        invoices = self.browse(self.ids)
        # Sysop - unkown i - quick fix. Todo: find what it means
        i=1
        for invoice in invoices:
            if invoice.move_id.id:
                # invoices that are signed can not be deleted
                if (invoice.type in ('out_refund','out_invoice') and not invoice.journal_id.self_billing) or (invoice.type in ('in_refund','in_invoice') and invoice.journal_id.self_billing ):
                    raise osv.except_osv(_('Error !'), _('You cannot cancel confirmed Invoices subject to digital signature!'))
                    return False

                account_move_obj.button_cancel([invoice.move_id.id])
                # delete the move this invoice was pointing to
                # Note that the corresponding move_lines and move_reconciles
                # will be automatically deleted too
                account_move_obj.unlink([i['move_id'][0]])
            if invoice.payment_ids:
                account_move_line_obj = self.pool.get('account.move.line')
                pay_ids = account_move_line_obj.browse(i['payment_ids'])
                for move_line in pay_ids:
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.line_partial_ids:
                        raise osv.except_osv(_('Error !'), _('You cannot cancel the Invoice which is Partially Paid! You need to unreconcile concerned payment entries!'))

        self.write(self.ids, {'state':'cancel', 'move_id':False})
        self._log_event(self.ids, -1.0, 'Cancel Invoice')
        return True


class sale_order(models.Model):
    _name = 'sale.order'
    _inherit = 'sale.order'

    so_hash = fields.Char(string="Assinatura", size=200, )
    so_hash_control = fields.Char(string="Chave", size=40, default=lambda *a: hash_control, )
    system_entry_date = fields.Datetime(string="Data de confirmação", required=False, )

    def get_hash(self, cr, uid, sale_order_id, context=None):
        res = {}
        sale_order = self.browse(cr, uid, sale_order_id, context=context)
        cr.execute("SELECT so_hash FROM sale_order inv WHERE id = (SELECT MAX(id) FROM sale_order)" )
        res = cr.fetchone()
        if res is None:
            return ''
        else :
            return res[0]

    @api.v7
    def action_signature(self, cr, uid, ids, context=None):
        """Write hash and system_entry_date """
        # duvida: usar esta accao ou adicionar action_sign a incluir num workflow redesenhado, que substitua o original ????

        for so in self.browse(cr, uid, ids, context=context):
            # if so.state in ('open', 'paid', 'cancel') # not necessary, wkf determines properlly when this action is called
            # continues when it is not necessary to sign the invoices
            # if (so.type in ('out_refund','out_invoice') and so.journal_id.self_billing) or (so.type in ('in_refund','in_invoice') and not so.journal_id.self_billing ) :
            #     continue
            so_date = str(so.date_order)
            now = so.system_entry_date or datetime.datetime.now()
            # try:
            #     invoiceNo = str(so.journal_id.saft_inv_type+' '+so.number)
            # except TypeError:
            #     raise osv.except_osv(_('Error !'), _("Please set the doc type at Journal's SAFT parameters!"))
            #     return
            # gross_total = self.grosstotal(so.id)
            prev_hash = self.get_hash(cr, uid, so.id, context=context)

            if not prev_hash:
                message = so_date + ';' + str(now)[:19].replace(' ', 'T')
            else:
                message = so_date + ';' + str(now)[:19].replace(' ', 'T') + ';' + prev_hash

            signature = os.popen('echo -n "' + message + '" | openssl dgst -sha1 -sign ' + priv_key + ' | openssl enc -base64 -A', "r").read()
            cr.execute("UPDATE sale_order SET so_hash = '%s' WHERE id = %d" % (signature, so.id))

            if not so.system_entry_date:
                cr.execute("UPDATE sale_order SET system_entry_date = '%s' WHERE id = %d" %(now, so.id) )
        return True

    @api.v7
    def action_button_confirm(self, cr, uid, ids, context=None):
        self.action_signature(cr, uid, ids, context)
        return super(sale_order, self).action_button_confirm(cr, uid, ids, context)
