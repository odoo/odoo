/** @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class CustomerFacingDisplayButton extends Component {
    static template = "point_of_sale.CustomerFacingDisplayButton";
    setup() {
        this.pos = usePos();
        this.customerDisplay = useState(useService("customer_display"));
        this.notification = useService("pos_notification");
    }
    get message() {
        const msg = {
            success: "",
            warning: _t("Connected, Not Owned"),
            failure: _t("Disconnected"),
            not_found: _t("Customer Screen Unsupported. Please upgrade the IoT Box"),
        }[this.customerDisplay.status];

        if (
            this.previousDisplayedStatus &&
            this.previousDisplayedStatus != this.customerDisplay.status
        ) {
            this.displayMessage(msg);
            this.previousDisplayedStatus = this.customerDisplay.status;
        }

        return msg;
    }
    displayMessage(message) {
        if (this.notification) {
            if (message.length == 0) {
                message = "Connected";
            }
            this.notification.add("Customer Display : " + message, 3000);
        }
    }
}
