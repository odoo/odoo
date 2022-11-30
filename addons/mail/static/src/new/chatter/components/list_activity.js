/** @odoo-module **/

import { ActivityButton } from "@mail/new/activity/activity_button";

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

export class ListActivity extends Component {
    get summaryText() {
        if (this.props.record.data.activity_exception_decoration) {
            return this.env._t("Warning");
        }
        if (this.props.record.data.activity_summary) {
            return this.props.record.data.activity_summary;
        }
        if (this.props.record.data.activity_type_id) {
            return this.props.record.data.activity_type_id[1 /** display_name **/];
        }
        return undefined;
    }
}

Object.assign(ListActivity, {
    components: { ActivityButton },
    // also used in children, in particular in ActivityButton
    fieldDependencies: {
        activity_exception_decoration: { type: "selection" },
        activity_exception_icon: { type: "char" },
        activity_state: { type: "selection" },
        activity_summary: { type: "char" },
        activity_type_icon: { type: "char" },
        activity_type_id: { type: "many2one", relation: "mail.activity.type" },
    },
    props: standardFieldProps,
    template: "mail.ListActivity",
});

registry.category("fields").add("list_activity", ListActivity);
