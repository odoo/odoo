odoo.define('point_of_sale.OrderWidget', function(require) {
    'use strict';

    const { useRef, onPatched } = owl.hooks;
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { Orderline } = require('point_of_sale.Orderline');
    const { OrderSummary } = require('point_of_sale.OrderSummary');

    class OrderWidget extends PosComponent {
        static template = 'OrderWidget';
        constructor() {
            super(...arguments);
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
            this.env.pos.on(
                'change:selectedOrder',
                () => {
                    this.trigger('new-orderline-selected');
                },
                this
            );
            this.order.orderlines.on(
                'new-orderline-selected',
                () => {
                    this.trigger('new-orderline-selected');
                },
                this
            );
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
                },
                this
            );
            this.order.on(
                'change',
                () => {
                    this.render();
                },
                this
            );
        }
        patched() {
            this.env.pos.off('change:selectedOrderline', null, this);
            this.order.orderlines.off('new-orderline-selected', null, this);
            this.order.orderlines.off('change', null, this);
            this.order.orderlines.off('add remove', null, this);
            this.order.off('change', null, this);

            this.env.pos.on(
                'change:selectedOrder',
                () => {
                    this.trigger('new-orderline-selected');
                },
                this
            );
            this.order.orderlines.on(
                'new-orderline-selected',
                () => {
                    this.trigger('new-orderline-selected');
                },
                this
            );
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
                },
                this
            );
            this.order.on(
                'change',
                () => {
                    this.render();
                },
                this
            );
        }
        willUnmount() {
            this.env.pos.off('change:selectedOrderline', null, this);
            this.order.orderlines.off('new-orderline-selected', null, this);
            this.order.orderlines.off('change', null, this);
            this.order.orderlines.off('add remove', null, this);
            this.order.off('change', null, this);
        }
        selectLine(event) {
            this.order.select_orderline(event.detail.orderline);
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
    }

    OrderWidget.components = { Orderline, OrderSummary };

    return { OrderWidget };
});
