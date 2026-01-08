/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class ContractWarningTooltip extends Component {
    get tooltipInfo() {
        return JSON.stringify({
            "text" : _t("Calendar Mismatch: The employee's calendar does not match this contract's calendar. This could lead to unexpected behaviors."),
        })
    }
}
ContractWarningTooltip.template = "hr_contract.ContractWarningTooltip";

export const contractWarningTooltip = {
    component: ContractWarningTooltip,
};
registry.category("view_widgets").add("contract_warning_tooltip", contractWarningTooltip);
