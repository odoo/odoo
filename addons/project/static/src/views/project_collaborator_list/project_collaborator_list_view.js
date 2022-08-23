/** @odoo-module */

import { registry } from "@web/core/registry";
import { listView } from '@web/views/list/list_view';
import { ProjectCollaboratorsListController } from './project_collaborator_list_controller';

export const ProjectCollaboratorsListView = {
    ...listView,
    Controller: ProjectCollaboratorsListController,
    buttonTemplate: 'collaborators.List_view.buttons',
};

registry.category('views').add('project_collaborators', ProjectCollaboratorsListView);
