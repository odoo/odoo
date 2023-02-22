/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

class ActivityException extends Component {
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
    fieldDependencies: [{ name: "activity_exception_icon", type: "char" }],
    noLabel: true,
});
