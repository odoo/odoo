/** @odoo-module */

import { registry } from "@web/core/registry";

const { Component } = owl;

class TraceBackFieldWidget extends Component {
}
TraceBackFieldWidget.template = "exception_tracker.TracebackFieldWidget"

registry.category("fields").add("traceback", TraceBackFieldWidget);

