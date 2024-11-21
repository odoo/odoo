/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class ContractWarningTooltip extends Component {
    static template = "hr_contract.ContractWarningTooltip";
    static props = { ...standardWidgetProps };
    get tooltipInfo() {
        return JSON.stringify({
            "text" : _t("Calendar Mismatch: The employee's calendar does not match this contract's calendar. This could lead to unexpected behaviors."),
        })
    }
}

export const contractWarningTooltip = {
    component: ContractWarningTooltip,
};
registry.category("view_widgets").add("contract_warning_tooltip", contractWarningTooltip);
