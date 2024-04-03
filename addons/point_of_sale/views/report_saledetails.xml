<?xml version="1.0" encoding="utf-8"?>
<openerp>
<data>
<template id="report_saledetails">
    <t t-set="company" t-value="env.company"/>
    <t t-call="web.html_container">
    <t t-call="web.internal_layout">
        <div class="page">

            <div class="text-center">
                <h2>Sales Details</h2>

                <t t-if="date_start and date_stop">
                    <strong><t t-esc="date_start" t-options="{'widget': 'datetime'}"/> - <t t-esc="date_stop" t-options="{'widget': 'datetime'}"/></strong>
                </t>
            </div>

            <!-- Orderlines -->
            <h3>Products</h3>
            <table  class="table table-sm">
                <thead><tr>
                    <th>Product</th>
                    <th>Quantity</th>
                    <th>Price Unit</th>
                </tr></thead>
                <tbody>
                <tr t-foreach='products' t-as='line'>
                    <t t-set="internal_reference" t-value="line['code'] and '[%s] ' % line['code'] or ''" />
                    <td><t t-esc="internal_reference" /><t t-esc="line['product_name']" /></td>
                    <td>
                        <t t-esc="line['quantity']" />
                        <t t-if='line["uom"] != "Units"'>
                            <t t-esc='line["uom"]' /> 
                        </t>
                    </td>
                    <td>
                        <t t-esc='line["price_unit"]' />
                    <t t-if='line["discount"] != 0'>
                        Disc: <t t-esc='line["discount"]' />%
                    </t>
                    </td>
                </tr>
                </tbody>
            </table>

            <br/>

            <h3>Payments</h3>
            <table  class="table table-sm">
                <thead><tr>
                    <th>Name</th>
                    <th>Total</th>
                </tr></thead>
                <tbody>
                <tr t-foreach='payments' t-as='payment'>
                    <td><t t-esc="payment['name']" /></td>
                    <td><t t-esc="payment['total']" t-options="{'widget': 'float', 'precision': currency_precision}"/></td>
                </tr>
                </tbody>
            </table>

            <br/>

            <h3>Taxes</h3>
            <table  class="table table-sm">
                <thead><tr>
                    <th>Name</th>
                    <th>Tax Amount</th>
                    <th>Base Amount</th>
                </tr></thead>
                <tbody>
                <tr t-foreach='taxes' t-as='tax'>
                    <td><t t-esc="tax['name']" /></td>
                    <td><t t-esc="tax['tax_amount']" t-options="{'widget': 'float', 'precision': currency_precision}"/></td>
                    <td><t t-esc="tax['base_amount']" t-options="{'widget': 'float', 'precision': currency_precision}"/></td>
                </tr>
                </tbody>
            </table>

            <br/>
            <br/>

            <strong>Total: <t t-esc='total_paid' t-options="{'widget': 'float', 'precision': currency_precision}"/></strong>

        </div>
    </t>
    </t>
</template>
</data>
</openerp>
