/* @odoo-module */

import { ActivityButton } from "@mail/core/web/activity_button";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class KanbanActivity extends Component {
    static components = { ActivityButton };
    // used in children, in particular in ActivityButton
    static fieldDependencies = [
        { name: "activity_exception_decoration", type: "selection" },
        { name: "activity_exception_icon", type: "char" },
        { name: "activity_state", type: "selection" },
        { name: "activity_summary", type: "char" },
        { name: "activity_type_icon", type: "char" },
        { name: "activity_type_id", type: "many2one", relation: "mail.activity.type" },
    ];
    static props = standardFieldProps;
    static template = "mail.KanbanActivity";
}

export const kanbanActivity = {
    component: KanbanActivity,
    fieldDependencies: KanbanActivity.fieldDependencies,
};

registry.category("fields").add("kanban_activity", kanbanActivity);
