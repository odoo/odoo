/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class SubtaskCounter extends Component {
    static template = "project.SubtaskCounter";
    static props = {
        ...standardWidgetProps,
    };

    onClick() {
        this.props.record.toggleSubtasksList();
    }

    get closedSubtaskCount() {
        return this.props.record.data.closed_subtask_count;
    }

    get subtaskCount() {
        return this.props.record.data.subtask_count;
    }

    get counterTitle() {
        return _t("%(closedCount)s sub-tasks closed out of %(totalCount)s", {
            closedCount: this.closedSubtaskCount,
            totalCount: this.subtaskCount,
        });
    }

    get counterDisplay() {
        return _t("%(count1)s/%(count2)s", {
            count1: this.closedSubtaskCount,
            count2: this.subtaskCount,
        });
    }
}

export const subtaskCounter = {
    component: SubtaskCounter,
    fieldDependencies: [
        { name: "closed_subtask_count", type: "integer" },
        { name: "subtask_count", type: "integer" },
    ],
};

registry.category("view_widgets").add("subtask_counter", subtaskCounter);
