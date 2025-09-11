/** @odoo-module */

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";


const { Component } = owl;

class LogFieldWidget extends Component {
    static template = "exception_tracker.LogFieldWidget";
}

export const logFieldWidget = {
    component: LogFieldWidget,
    displayName: _lt("Logs"),
};

registry.category("fields").add("log", logFieldWidget);

