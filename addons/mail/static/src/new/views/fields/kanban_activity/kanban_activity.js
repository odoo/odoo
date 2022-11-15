/** @odoo-module **/

import { ActivityButton } from "@mail/new/activity/activity_button";

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

import { Component } from "@odoo/owl";

export class KanbanActivity extends Component {}

Object.assign(KanbanActivity, {
    components: { ActivityButton },
    // used in children, in particular in ActivityButton
    fieldDependencies: {
        activity_exception_decoration: { type: "selection" },
        activity_exception_icon: { type: "char" },
        activity_state: { type: "selection" },
        activity_type_icon: { type: "char" },
    },
    props: standardFieldProps,
    template: "mail.KanbanActivity",
});

registry.category("fields").add("kanban_activity", KanbanActivity);
