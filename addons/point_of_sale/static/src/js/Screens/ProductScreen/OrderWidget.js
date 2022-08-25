odoo.define('point_of_sale.OrderWidget', function(require) {
    'use strict';

    const { useListener } = require("@web/core/utils/hooks");
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    const { onPatched, useRef } = owl;

    class OrderWidget extends PosComponent {
        setup() {
            super.setup();
            useListener('select-line', this._selectLine);
            useListener('edit-pack-lot-lines', this._editPackLotLines);
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
            return this.order ? this.order.get_orderlines() : [];
        }
        _selectLine(event) {
            this.order.select_orderline(event.detail.orderline);
        }
        // IMPROVEMENT: Might be better to lift this to ProductScreen
        // because there is similar operation when clicking a product.
        //
        // Furthermore, what if a number different from 1 (or -1) is specified
        // to an orderline that has product tracked by lot. Lot tracking (based
        // on the current implementation) requires that 1 item per orderline is
        // allowed.
        async _editPackLotLines(event) {
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
    OrderWidget.template = 'OrderWidget';

    Registries.Component.add(OrderWidget);

    return OrderWidget;
});
