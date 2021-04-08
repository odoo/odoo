odoo.define('pos_sale.SaleOrderRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    /**
     * @props {models.Order} order
     * @props columns
     * @emits click-order
     */
    class SaleOrderRow extends PosComponent {
        get order() {
            return this.props.order;
        }
        get highlighted() {
            const highlightedOrder = this.props.highlightedOrder;
            return !highlightedOrder ? false : highlightedOrder.backendId === this.props.order.backendId;
        }

        // Column getters //

        get name() {
            return this.order.name;
        }
        get date() {
            return moment(this.order.date_order).format('YYYY-MM-DD hh:mm A');
        }
        get customer() {
            const customer = this.order.partner_id;
            return customer ? customer[1] : null;
        }
        get total() {
            return this.env.pos.format_currency(this.order.amount_total);
        }
        get state() {
            let state_mapping = {
              'draft': this.env._t('Quotation'),
              'sent': this.env._t('Quotation Sent'),
              'sale': this.env._t('Sales Order'),
              'done': this.env._t('Locked'),
              'cancel': this.env._t('Cancelled'),
            };

            return state_mapping[this.order.state];
        }
        get salesman() {
            const salesman = this.order.user_id;
            return salesman ? salesman[1] : null;
        }
    }
    SaleOrderRow.template = 'SaleOrderRow';

    Registries.Component.add(SaleOrderRow);

    return SaleOrderRow;
});
