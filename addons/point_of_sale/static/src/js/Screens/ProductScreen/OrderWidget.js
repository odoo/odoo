/** @odoo-module */

import { useListener } from "@web/core/utils/hooks";
import { PosComponent } from "@point_of_sale/js/PosComponent";
import { EditListPopup } from "@point_of_sale/js/Popups/EditListPopup";

import { Orderline } from "./Orderline";
import { OrderSummary } from "./OrderSummary";

const { useEffect, useRef } = owl;

export class OrderWidget extends PosComponent {
    static components = { Orderline, OrderSummary };
    static template = "OrderWidget";

    setup() {
        super.setup();
        useListener("select-line", this._selectLine);
        useListener("edit-pack-lot-lines", this._editPackLotLines);
        this.scrollableRef = useRef("scrollable");
        useEffect(
            () => {
                const selectedLineEl = this.scrollableRef.el && this.scrollableRef.el.querySelector(".orderline.selected");
                if(selectedLineEl) {
                    selectedLineEl.scrollIntoView({ behavior: "smooth", block: "start" });
                }
            },
            () => [this.order.selected_orderline]
        );
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
        const { confirmed, payload } = await this.showPopup(EditListPopup, {
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
        this.order.select_orderline(event.detail.orderline);
    }
}
