odoo.define('point_of_sale.OrderWidget', function(require) {
    'use strict';

    const { useRef, onPatched } = owl.hooks;
    const { Component } = owl;

    class Orderline extends Component {
        constructor() {
            super(...arguments);
            this.line = this.props.line;
            this.pos = this.props.pos;
        }
        selectLine() {
            this.trigger('select-line', { orderline: this.line });
        }
        lotIconClicked() {
            this.trigger('show-product-lot', { orderline: this.line });
        }
    }

    class OrderSummary extends Component {
        constructor() {
            super(...arguments);
            this.order = this.props.order;
            this.pos = this.props.pos;
            this.update();
        }
        mounted() {
            this.order.orderlines.on('change', () => {
                this.update();
            });
        }
        update() {
            const total = this.order ? this.order.get_total_with_tax() : 0;
            const tax = this.order ? total - this.order.get_total_without_tax() : 0;
            this.total = this.pos.format_currency(total);
            this.tax = this.pos.format_currency(tax);
        }
    }

    class OrderWidget extends Component {
        constructor() {
            super(...arguments);
            this.pos = this.props.pos;
            this.order = this.props.order;
            this.numpadState = this.props.numpadState;
            this.orderlinesArray = this.order.get_orderlines();
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
        mounted() {
            this.numpadState.on('set_value', this.set_value, this);
            this.order.orderlines.on('change', () => {
                this.render();
            });
            this.order.orderlines.on('add remove', () => {
                this.scrollToBottom = true;
                this.render();
                this.numpadState.reset();
            });
            this.order.on('change', () => {
                this.numpadState.reset();
                this.render();
            });
        }
        willUnmount() {
            this.numpadState.off();
            this.order.orderlines.off();
            this.order.off();
        }
        selectLine(event) {
            this.order.select_orderline(event.detail.orderline);
            this.numpadState.reset();
        }
        showProductLot(event) {
            this.order.select_orderline(event.detail.orderline);
            this.order.display_lot_popup();
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
                if (this.pos.config.iface_customer_facing_display) {
                    this.pos.send_current_order_to_customer_facing_display();
                }
            }
        }
    }

    OrderWidget.components = { Orderline, OrderSummary };

    return { OrderWidget, Orderline, OrderSummary }
});
