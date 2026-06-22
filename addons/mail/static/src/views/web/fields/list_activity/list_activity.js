import { ActivityButton } from "@mail/core/web/activity_button";

import { Component, props, types } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Record } from "@web/model/relational_model/record";

class ListActivityButton extends ActivityButton {
    static template = "mail.ListActivityButton";

    setup() {
        super.setup();
        this.props = props({ record: types.instanceOf(Record), slots: types.object().optional() });
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
    static template = "mail.ListActivity";

    setup() {
        super.setup();
        this.props = props({ record: types.instanceOf(Record) });
    }

    get summaryText() {
        if (this.props.record.data.activity_exception_decoration) {
            return _t("Warning");
        }
        if (this.props.record.data.activity_summary) {
            return this.props.record.data.activity_summary;
        }
        if (this.props.record.data.activity_type_id) {
            return this.props.record.data.activity_type_id.display_name;
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
