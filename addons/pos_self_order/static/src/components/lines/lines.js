/** @odoo-module */

import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/self_order_service";
import { _t } from "@web/core/l10n/translation";
import { extractProductNameAndAttributes } from "../../utils";
import { useService } from "@web/core/utils/hooks";

export class Lines extends Component {
    static template = "pos_self_order.Lines";
    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
    }

    get lines() {
        return this.props.order.lines;
    }

    clickOnLine(line) {
        const order = this.props.order;
        this.selfOrder.editedLine = line;
        if (
            !order.access_token ||
            (order.state === "draft" && this.selfOrder.self_order_mode === "meal")
        ) {
            this.selfOrder.editedOrder = order;
            this.router.navigate("product", { product_id: line.product_id });
        } else {
            this.selfOrder.notification.add(_t("You cannot edit an posted order!"), {
                type: "danger",
            });
        }
    }

    getNameAndDescription(line) {
        const productInfos = extractProductNameAndAttributes(line.full_product_name);
        return productInfos;
    }
}
