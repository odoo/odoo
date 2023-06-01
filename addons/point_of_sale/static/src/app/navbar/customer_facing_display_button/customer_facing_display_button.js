/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class CustomerFacingDisplayButton extends Component {
    static template = "CustomerFacingDisplayButton";
    setup() {
        this.pos = usePos();
        this.customerDisplay = useState(useService("customer_display"));
    }
    get message() {
        return {
            success: "",
            warning: _t("Connected, Not Owned"),
            failure: _t("Disconnected"),
            not_found: _t("Customer Screen Unsupported. Please upgrade the IoT Box"),
        }[this.customerDisplay.status];
    }
}
