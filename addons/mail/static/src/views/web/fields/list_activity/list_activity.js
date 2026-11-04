import { ActivityButton } from "@mail/core/web/activity_button";

import { Component } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class ListActivityButton extends ActivityButton {
    static props = {
        ...ActivityButton.props,
        slots: Object,
    };
    static template = "mail.ListActivityButton";

    setup() {
        super.setup();
        this.defaultActivityStateClass = "";
        this.defaultActivityDecorationClass = "fa-clock-o";
    }
}

export class ListActivity extends Component {
    static components = { ActivityButton: ListActivityButton };
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
    displayName: _t("List Activity"),
    supportedTypes: ["one2many"],
};

registry.category("fields").add("list_activity", listActivity);
