import { ActivityButton } from "@mail/core/web/activity_button";

import { Component, types, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Record } from "@web/model/relational_model/record";

export class KanbanActivity extends Component {
    static components = { ActivityButton };
    // used in children, in particular in ActivityButton
    static fieldDependencies = [
        {
            name: "activity_exception_decoration",
            type: "selection",
            selection: [
                ["warning", "Alert"],
                ["danger", "Error"],
            ],
        },
        { name: "activity_exception_icon", type: "char" },
        { name: "activity_state", type: "selection" },
        { name: "activity_summary", type: "char" },
        { name: "activity_type_icon", type: "char" },
        { name: "activity_type_id", type: "many2one", relation: "mail.activity.type" },
    ];
    static template = "mail.KanbanActivity";

    setup() {
        super.setup(...arguments);
        this.props = useProps({
            record: types.instanceOf(Record),
            buttonClasses: types.string().optional(),
        });
    }
}

export const kanbanActivity = {
    component: KanbanActivity,
    fieldDependencies: KanbanActivity.fieldDependencies,
    supportedOptions: [
        {
            label: _t("Button classes"),
            name: "button_classes",
            type: "string",
        },
    ],
    extractProps: ({ options }) => ({
        buttonClasses: options.button_classes,
    }),
};

registry.category("fields").add("kanban_activity", kanbanActivity);
