/** @odoo-module */

import { registry } from '@web/core/registry';
import { CharField } from '@web/views/fields/char/char_field';
import { formatChar } from '@web/views/fields/formatters';

class ProjectTaskNameWithSubtaskCountCharField extends CharField {
    get formattedSubtaskCount() {
        return formatChar(this.props.record.data.allow_subtasks && this.props.record.data.child_text || '');
    }
}

ProjectTaskNameWithSubtaskCountCharField.template = 'project.ProjectTaskNameWithSubtaskCountCharField';

registry.category('fields').add('name_with_subtask_count', ProjectTaskNameWithSubtaskCountCharField);
