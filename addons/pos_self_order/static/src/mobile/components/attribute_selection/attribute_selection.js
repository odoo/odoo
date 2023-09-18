/** @odoo-module */

import { AttributeSelector } from "@pos_self_order/common/components/attribute_selector/attribute_selector";
import { useSelfOrder } from "@pos_self_order/mobile/self_order_mobile_service";

export class AttributeSelection extends AttributeSelector {
    static template = "pos_self_order.AttributeSelection";

    setup() {
        this.selfOrder = useSelfOrder();
        super.setup();
    }

    get disableAttributes() {
        const order = this.selfOrder.currentOrder;

        return (
            this.selfOrder.editedLine &&
            this.selfOrder.editedLine.uuid &&
            order.lastChangesSent[this.selfOrder.editedLine.uuid]
        );
    }
}
