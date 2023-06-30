/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { EditListPopup } from "@point_of_sale/app/store/select_lot_popup/select_lot_popup";

import { Orderline } from "@point_of_sale/app/screens/product_screen/orderline/orderline";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { Component, useEffect, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class OrderWidget extends Component {
    static components = { Orderline, OrderSummary };
    static template = "point_of_sale.OrderWidget";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
        this.numberBuffer = useService("number_buffer");
        this.scrollableRef = useRef("scrollable");
        useEffect(
            () => {
                const selectedLineEl =
                    this.scrollableRef.el &&
                    this.scrollableRef.el.querySelector(".orderline.selected");
                if (selectedLineEl) {
                    selectedLineEl.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            },
            () => [this.order.selected_orderline]
        );
    }
    get order() {
        return this.pos.get_order();
    }
    get orderlinesArray() {
        return this.order ? this.order.get_orderlines() : [];
    }
    selectLine(orderline) {
        this.numberBuffer.reset();
        this.order.select_orderline(orderline);
    }
    // IMPROVEMENT: Might be better to lift this to ProductScreen
    // because there is similar operation when clicking a product.
    //
    // Furthermore, what if a number different from 1 (or -1) is specified
    // to an orderline that has product tracked by lot. Lot tracking (based
    // on the current implementation) requires that 1 item per orderline is
    // allowed.
    async editPackLotLines(orderline) {
        const isAllowOnlyOneLot = orderline.product.isAllowOnlyOneLot();
        const packLotLinesToEdit = orderline.getPackLotLinesToEdit(isAllowOnlyOneLot);
        const { confirmed, payload } = await this.popup.add(EditListPopup, {
            title: this.env._t("Lot/Serial Number(s) Required"),
            name: orderline.product.display_name,
            isSingleItem: isAllowOnlyOneLot,
            array: packLotLinesToEdit,
        });
        if (confirmed) {
            // Segregate the old and new packlot lines
            const modifiedPackLotLines = Object.fromEntries(
                payload.newArray.filter((item) => item.id).map((item) => [item.id, item.text])
            );
            const newPackLotLines = payload.newArray
                .filter((item) => !item.id)
                .map((item) => ({ lot_name: item.text }));

            orderline.setPackLotLines({ modifiedPackLotLines, newPackLotLines });
        }
        this.order.select_orderline(orderline);
    }
}
