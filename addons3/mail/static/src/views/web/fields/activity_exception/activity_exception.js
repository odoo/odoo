/* @odoo-module */

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class ActivityException extends Component {
    static props = standardFieldProps;
    static template = "mail.ActivityException";
    static fieldDependencies = [{ name: "activity_exception_icon", type: "char" }];
    static noLabel = true;

    get textClass() {
        if (this.props.record.data[this.props.name]) {
            return (
                "text-" +
                this.props.record.data[this.props.name] +
                " fa " +
                this.props.record.data.activity_exception_icon
            );
        }
        return undefined;
    }
}

Object.assign(ActivityException, {
    props: standardFieldProps,
    template: "mail.ActivityException",
});

registry.category("fields").add("activity_exception", {
    component: ActivityException,
    fieldDependencies: ActivityException.fieldDependencies,
    noLabel: true,
});
