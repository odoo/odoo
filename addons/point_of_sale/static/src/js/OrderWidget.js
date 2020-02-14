odoo.define('point_of_sale.OrderWidget', function(require) {
    'use strict';

    const { useRef, onPatched } = owl.hooks;
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { Orderline } = require('point_of_sale.Orderline');
    const { OrderSummary } = require('point_of_sale.OrderSummary');

    class OrderWidget extends PosComponent {
        constructor() {
            super(...arguments);
            this.numpadState = this.props.numpadState;
            this.numpadState.reset();
            this.scrollableRef = useRef('scrollable');
            this.scrollToBottom = false;
            onPatched(() => {
                // IMPROVEMENT
                // This one just stays at the bottom of the orderlines list.
                // Perhaps it is better to scroll to the added or modified orderline.
                if (this.scrollToBottom) {
                    this.scrollableRef.el.scrollTop = this.scrollableRef.el.scrollHeight;
                    this.scrollToBottom = false;
                }
            });
        }
        get order() {
            return this.env.pos.get_order();
        }
        get orderlinesArray() {
            return this.order.get_orderlines();
        }
        mounted() {
            this.numpadState.on('set_value', this.set_value, this);
            this.order.orderlines.on(
                'change',
                () => {
                    this.render();
                },
                this
            );
            this.order.orderlines.on(
                'add remove',
                () => {
                    this.scrollToBottom = true;
                    this.render();
                    this.numpadState.reset();
                },
                this
            );
            this.order.on(
                'change',
                () => {
                    this.numpadState.reset();
                    this.render();
                },
                this
            );
        }
        patched() {
            this.numpadState.off('set_value', null, this);
            this.order.orderlines.off('change', null, this);
            this.order.orderlines.off('add remove', null, this);
            this.order.off('change', null, this);

            this.numpadState.on('set_value', this.set_value, this);
            this.order.orderlines.on(
                'change',
                () => {
                    this.render();
                },
                this
            );
            this.order.orderlines.on(
                'add remove',
                () => {
                    this.scrollToBottom = true;
                    this.render();
                    this.numpadState.reset();
                },
                this
            );
            this.order.on(
                'change',
                () => {
                    this.numpadState.reset();
                    this.render();
                },
                this
            );
        }
        willUnmount() {
            this.numpadState.off('set_value', null, this);
            this.order.orderlines.off('change', null, this);
            this.order.orderlines.off('add remove', null, this);
            this.order.off('change', null, this);
        }
        selectLine(event) {
            this.order.select_orderline(event.detail.orderline);
            this.numpadState.reset();
        }
        // TODO jcb: Might be better to lift this to ProductScreen
        // because there is similar operation when clicking a product.
        //
        // Furthermore, what if a number different from 1 (or -1) is specified
        // to an orderline that has product tracked by lot. Lot tracking (based
        // on the current implementation) requires that 1 item per orderline is
        // allowed.
        async editPackLotLines(event) {
            const orderline = event.detail.orderline;
            const isAllowOnlyOneLot = orderline.product.isAllowOnlyOneLot();
            const packLotLinesToEdit = orderline.getPackLotLinesToEdit(isAllowOnlyOneLot);
            const { confirmed, payload } = await this.showPopup('EditListPopup', {
                title: this.env._t('Lot/Serial Number(s) Required'),
                isSingleItem: isAllowOnlyOneLot,
                array: packLotLinesToEdit,
            });
            if (confirmed) {
                // Segregate the old and new packlot lines
                const modifiedPackLotLines = Object.fromEntries(
                    payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                );
                const newPackLotLines = payload.newArray
                    .filter(item => !item.id)
                    .map(item => ({ lot_name: item.text }));

                orderline.setPackLotLines({ modifiedPackLotLines, newPackLotLines });
            }
            this.order.select_orderline(event.detail.orderline);
        }
        set_value(val) {
            if (this.order.get_selected_orderline()) {
                var mode = this.numpadState.get('mode');
                if (mode === 'quantity') {
                    this.order.get_selected_orderline().set_quantity(val);
                } else if (mode === 'discount') {
                    this.order.get_selected_orderline().set_discount(val);
                } else if (mode === 'price') {
                    var selected_orderline = this.order.get_selected_orderline();
                    selected_orderline.price_manually_set = true;
                    selected_orderline.set_unit_price(val);
                }
                if (this.env.pos.config.iface_customer_facing_display) {
                    this.env.pos.send_current_order_to_customer_facing_display();
                }
            }
        }
    }

    OrderWidget.components = { Orderline, OrderSummary };

    return { OrderWidget };
});
