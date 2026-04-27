/** @odoo-module */

import { Component, useState } from "@odoo/owl";

export class AccountReportButtonsBar extends Component {
    static template = "account_reports.AccountReportButtonsBar";
    static props = {};

    setup() {
        this.controller = useState(this.env.controller);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Buttons
    //------------------------------------------------------------------------------------------------------------------
    get barButtons() {
        const buttons = [];

        for (const button of this.controller.buttons) {
            if (button.always_show) {
                buttons.push(button);
            }
        }

        return buttons;
    }
}
