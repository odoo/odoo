/** @odoo-module */

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useselfOrder } from "@pos_self_order/kiosk/self_order_kiosk_service";
import { KioskTemplate } from "@pos_self_order/kiosk/template/kiosk_template";

export class OrderCart extends Component {
    static template = "pos_self_order.OrderCart";
    static components = { KioskTemplate };

    setup() {
        this.selfOrder = useselfOrder();
        this.router = useService("router");
    }

    get lines() {
        const lines = this.selfOrder.currentOrder.lines;
        return lines ? lines : [];
    }

    backToMenu() {
        this.router.navigate("product_list");
    }

    pay() {
        if (this.selfOrder.kiosk_mode === "table" && !this.selfOrder.currentOrder.take_away) {
            this.router.navigate("stand_number");
        } else {
            this.router.navigate("payment");
        }
    }

    async removeLine(lineUuid) {
        this.selfOrder.currentOrder.removeLine(lineUuid);
        await this.selfOrder.getPricesFromServer();
    }

    getChildLines(line) {
        return this.lines.filter((l) => l.combo_parent_uuid === line.uuid);
    }

    getPrice(line) {
        const childLines = this.getChildLines(line);
        if (childLines.length == 0) {
            return line.price_subtotal_incl;
        } else {
            let price = 0;
            for (const child of childLines) {
                price += child.price_subtotal_incl;
            }
            return price;
        }
    }

    async changeQuantity(line, increase, fetch = true) {
        if (!increase && line.qty === 1) {
            this.removeLine(line.uuid);
            return;
        }
        increase ? line.qty++ : line.qty--;
        for (const cline of this.selfOrder.currentOrder.lines) {
            if (cline.combo_parent_uuid === line.uuid) {
                this.changeQuantity(cline, increase, false);
            }
        }
        if (fetch) {
            await this.selfOrder.getPricesFromServer();
        }
        return;
    }

    getAttributes(attributes){
        //attribute traduction
        return attributes;
    }
}
