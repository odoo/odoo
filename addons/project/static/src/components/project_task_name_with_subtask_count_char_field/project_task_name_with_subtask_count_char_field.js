import { registry } from '@web/core/registry';
import { CharField, charField } from '@web/views/fields/char/char_field';

export class ProjectTaskNameWithSubtaskCountCharField extends CharField {
    static template = "project.ProjectTaskNameWithSubtaskCountCharField";
}

export const projectTaskNameWithSubtaskCountCharField = {
    ...charField,
    component: ProjectTaskNameWithSubtaskCountCharField,
    fieldDependencies: [
        { name: "subtask_count", type: "integer" },
        { name: "closed_subtask_count", type: "integer" },
    ],
}
registry.category("fields").add("name_with_subtask_count", projectTaskNameWithSubtaskCountCharField);
