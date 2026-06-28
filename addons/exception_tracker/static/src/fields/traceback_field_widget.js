/** @odoo-module */

import { registry } from "@web/core/registry";
import { _lt } from "@web/core/l10n/translation";

const { Component } = owl;
export class TraceBackFieldWidget extends Component {
    static template = "exception_tracker.TracebackFieldWidget";
}

export const traceBackFieldWidget = {
    component: TraceBackFieldWidget,
    displayName: _lt("Traceback"),
};

registry.category("fields").add("traceback", traceBackFieldWidget);
