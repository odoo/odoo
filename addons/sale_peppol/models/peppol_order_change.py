from odoo import fields, models


class PeppolOrderChange(models.Model):
    _name = 'peppol.order.change'
    _description = 'PEPPOL order documents information'
    _order = 'sequence, id'

    order_id = fields.Many2one(
        'sale.order',
        string="Order",
        required=True,
        ondelete='cascade',
    )
    peppol_attachment_id = fields.Many2one('ir.attachment')
    sequence = fields.Integer(string="Order change sequence number")
    state = fields.Selection([
        ('received', 'Received'),
        ('replied', 'Replied'),
    ], default='received')

    def peppol_send_order_response_advanced(self, response_code):
        # Currently only support AB or AP
        code_list = [
            'AB',  # Ack
            'AP',  # Accepted
        ]
        # Generate Order Response document using ubl_bis or something
        # For now let's just send order response with AP option only.
        if response_code not in code_list:
            return
        response_xml = self.env['purchase.edi.xml.ubl_bis3_advanced_order']._generate_order_response(sale_order, response_code)
        # Send generated document to Peppol
        print(response_xml)
