import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { X2ManyField, x2ManyField } from '@web/views/fields/x2many/x2many_field';

import { SubtaskListRenderer } from './subtask_list_renderer';

export class SubtaskOne2ManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: SubtaskListRenderer,
    };

    async switchToForm(record, options) {
        await this.props.record.save();
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                views: [[false, "form"]],
                res_id: record.resId,
                res_model: this.list.resModel,
                context: pick(this.props.context, "active_test", "default_project_id"),
            },
            {
                props: { resIds: this.list.resIds },
                newWindow: options.newWindow,
            }
        );
    }
}

export const subtaskOne2ManyField = {
    ...x2ManyField,
    component: SubtaskOne2ManyField,
    additionalClasses: ["o_field_one2many"],
}

registry.category("fields").add("subtasks_one2many", subtaskOne2ManyField);
