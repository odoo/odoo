/** @odoo-module */

import { registry } from '@web/core/registry';
import { CharField, charField } from '@web/views/fields/char/char_field';
import { formatChar } from '@web/views/fields/formatters';

class ProjectTaskNameWithSubtaskCountCharField extends CharField {
    get formattedSubtaskCount() {
        return formatChar(this.props.record.data.subtask_count ? `(${this.props.record.data.open_subtask_count}/${this.props.record.data.subtask_count} subtask${this.props.record.data.subtask_count>1 ? 's' : ''})`  : '');
    }
}

ProjectTaskNameWithSubtaskCountCharField.template = 'project.ProjectTaskNameWithSubtaskCountCharField';

registry.category("fields").add("name_with_subtask_count", {
    ...charField,
    component: ProjectTaskNameWithSubtaskCountCharField,
});
