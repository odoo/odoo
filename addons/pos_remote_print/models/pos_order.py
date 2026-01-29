from odoo import models, api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def claim_remote_print(self, order_id, session_id):
        """
        Atomic claim of a print job.
        Returns True if the session successfully claimed it.
        """
        order = self.browse(order_id)
        if not order.exists():
            return False
            
        # Already printed?
        if order.is_remote_printed:
            return False
            
        # Check if another session locked it (concurrency)
        if order.remote_printer_lock and order.remote_printer_lock.id != session_id:
            return False
            
        # Lock it and Mark as printed (optimistic)
        # In real world, we might want to mark 'printing' then 'printed' after success,
        # but for now we claim and assume success to prevent double print.
        valid = False
        if not order.remote_printer_lock:
             order.write({
                 'remote_printer_lock': session_id,
                 'is_remote_printed': True
             })
             valid = True
             
        return valid
