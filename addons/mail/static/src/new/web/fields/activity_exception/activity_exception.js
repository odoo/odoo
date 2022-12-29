/* @odoo-module */

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

class ActivityException extends Component {
    static props = standardFieldProps;
    static template = "mail.ActivityException";
    static fieldDependencies = {
        activity_exception_icon: { type: "char" },
    };
    static noLabel = true;

    get textClass() {
        if (this.props.value) {
            return `text-${this.props.value} fa ${this.props.record.data.activity_exception_icon}`;
        }
        return undefined;
    }
}

registry.category("fields").add("activity_exception", ActivityException);
