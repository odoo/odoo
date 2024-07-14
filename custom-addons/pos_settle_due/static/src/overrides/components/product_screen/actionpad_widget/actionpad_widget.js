/** @odoo-module */

import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";

patch(ActionpadWidget.prototype, {
    get partnerInfos() {
        return this.pos.getPartnerCredit(this.props.partner);
    },
});
