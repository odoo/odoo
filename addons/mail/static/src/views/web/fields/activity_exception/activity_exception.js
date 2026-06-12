import { Component, props, types } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { Record } from "@web/model/relational_model/record";

class ActivityException extends Component {
    static template = "mail.ActivityException";
    static fieldDependencies = [{ name: "activity_exception_icon", type: "char" }];

    setup() {
        super.setup(...arguments);
        this.props = props({ name: types.string(), record: types.instanceOf(Record) });
    }

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

registry.category("fields").add("activity_exception", {
    component: ActivityException,
    fieldDependencies: ActivityException.fieldDependencies,
    label: false,
});
