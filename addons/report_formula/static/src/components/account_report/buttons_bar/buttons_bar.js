/** @odoo-module native */
import { Component, useState } from "@odoo/owl";

export class AccountReportButtonsBar extends Component {
    static template = "report_formula.AccountReportButtonsBar";
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
