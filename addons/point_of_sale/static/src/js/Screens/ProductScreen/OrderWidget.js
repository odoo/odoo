/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { EditListPopup } from "@point_of_sale/js/Popups/EditListPopup";

import { Orderline } from "./Orderline";
import { OrderSummary } from "./OrderSummary";
import { Component, useEffect, useRef, onWillStart } from "@odoo/owl";

export class OrderWidget extends Component {
    static components = { Orderline, OrderSummary };
    static template = "OrderWidget";

    setup() {
        super.setup();
        this.popup = useService("popup");
        this.numberBuffer = useService("number_buffer");
        this.orm = useService("orm");
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
        onWillStart(this.findIfOrderIsTrusted);
    }

    async findIfOrderIsTrusted() {
        const resp = await this.orm.searchRead(
            "pos.order",
            [["pos_reference", "=", this.order.name]],
            ["is_trusted"]
        );
        this.order.is_trusted = resp.length ? resp[0].is_trusted : true;
        console.log("this.order :>> ", this.order);
    }

    trustOrder() {
        this.orm.write("pos.order", [this.order.server_id], { is_trusted: true });
        this.order.is_trusted = true;
    }

    get order() {
        return this.env.pos.get_order();
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
