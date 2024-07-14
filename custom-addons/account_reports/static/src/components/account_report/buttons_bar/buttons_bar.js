/** @odoo-module */

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component, useState } from "@odoo/owl";

export class AccountReportButtonsBar extends Component {
    static template = "account_reports.AccountReportButtonsBar";
    static props = {};

    static components = {
        Dropdown,
        DropdownItem,
    };

    setup() {
        this.controller = useState(this.env.controller);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Buttons
    //------------------------------------------------------------------------------------------------------------------
    get groupedButtons() {
        const buttons= [];

        for (const button of this.controller.buttons)
            if (!button.always_show)
                buttons.push(button);

        return buttons;
    }

    get singleButtons() {
        const buttons= [];

        for (const button of this.controller.buttons)
            if (button.always_show)
                buttons.push(button);

        return buttons;
    }
}
