/** @odoo-module **/

import {Component, useState} from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";


export class AccountReportCogMenu extends Component {
    static template = "account_reports.AccountReportCogMenu";
    static components = {Dropdown, DropdownItem};
    static props = {};

    setup() {
        this.controller = useState(this.env.controller);
    }

    //------------------------------------------------------------------------------------------------------------------
    // Buttons
    //------------------------------------------------------------------------------------------------------------------
    get cogButtons() {
        const buttons = [];

        for (const button of this.controller.buttons) {
            if (!button.always_show) {
                buttons.push(button);
            }
        }

        return buttons;
    }
}
