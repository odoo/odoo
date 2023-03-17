/** @odoo-module */

import { registry } from '@web/core/registry';
import { CharField, charField } from '@web/views/fields/char/char_field';

class ProjectTaskNameWithSubtaskCountCharField extends CharField {
    get formattedSubtaskCount() {
            return this.props.record.data.subtask_count
                ? `(${this.props.record.data.closed_subtask_count}/${this.props.record.data.subtask_count} subtasks)`
                : "";
    }
}

ProjectTaskNameWithSubtaskCountCharField.template = 'project.ProjectTaskNameWithSubtaskCountCharField';

registry.category("fields").add("name_with_subtask_count", {
    ...charField,
    component: ProjectTaskNameWithSubtaskCountCharField,
});
