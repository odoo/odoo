/** @odoo-module */

const { Component } = owl;
import { useSelfOrder } from "@pos_self_order/SelfOrderService";

export class LandingPageHeader extends Component {
    setup() {
        this.selfOrder = useSelfOrder();
    }
}
LandingPageHeader.template = "LandingPageHeader";
export default { LandingPageHeader };
