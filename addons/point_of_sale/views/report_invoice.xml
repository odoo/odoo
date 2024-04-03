<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="point_of_sale.report_invoice_document" inherit_id="account.report_invoice_document">
        <xpath expr="//i[hasclass('oe_payment_label')]" position="inside">
            <t t-if="payment_vals.get('pos_payment_name')">
                using <t t-esc="payment_vals['pos_payment_name']" />
            </t>
        </xpath>
    </template>
</odoo>
