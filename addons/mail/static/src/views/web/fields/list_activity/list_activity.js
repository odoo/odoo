/* @odoo-module */

import { ActivityButton } from "@mail/core/web/activity_button";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ListActivity extends Component {
    static components = { ActivityButton };
    // also used in children, in particular in ActivityButton
    static fieldDependencies = [
        { name: "activity_exception_decoration", type: "selection", selection: [] },
        { name: "activity_exception_icon", type: "char" },
        { name: "activity_state", type: "selection", selection: [] },
        { name: "activity_summary", type: "char" },
        { name: "activity_type_icon", type: "char" },
        { name: "activity_type_id", type: "many2one", relation: "mail.activity.type" },
    ];
    static props = standardFieldProps;
    static template = "mail.ListActivity";

    get summaryText() {
        if (this.props.record.data.activity_exception_decoration) {
            return _t("Warning");
        }
        if (this.props.record.data.activity_summary) {
            return this.props.record.data.activity_summary;
        }
        if (this.props.record.data.activity_type_id) {
            return this.props.record.data.activity_type_id[1 /* display_name */];
        }
        return undefined;
    }
}

export const listActivity = {
    component: ListActivity,
    fieldDependencies: ListActivity.fieldDependencies,
};

registry.category("fields").add("list_activity", listActivity);
