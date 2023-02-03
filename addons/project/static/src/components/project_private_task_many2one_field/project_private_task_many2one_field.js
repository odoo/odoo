/** @odoo-module */

import { registry } from '@web/core/registry';
import { Many2OneField, many2OneField } from '@web/views/fields/many2one/many2one_field';

export class ProjectPrivateTaskMany2OneField extends Many2OneField { }
ProjectPrivateTaskMany2OneField.template = 'project.ProjectPrivateTaskMany2OneField';

export const projectPrivateTaskMany2OneField = {
    ...many2OneField,
    component: ProjectPrivateTaskMany2OneField,
};

registry.category("fields").add("project_private_task", projectPrivateTaskMany2OneField);
