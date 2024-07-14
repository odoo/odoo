/** @odoo-module **/

import { StreamPostKanbanController } from './stream_post_kanban_controller';
import { StreamPostKanbanModel } from './stream_post_kanban_model';
import { StreamPostKanbanRenderer } from './stream_post_kanban_renderer';

import { kanbanView } from '@web/views/kanban/kanban_view';
import { registry } from '@web/core/registry';

export const StreamPostKanbanView = {
    ...kanbanView,
    Controller: StreamPostKanbanController,
    Model: StreamPostKanbanModel,
    Renderer: StreamPostKanbanRenderer,
    buttonTemplate: 'StreamPostKanbanView.buttons',
};

registry.category("views").add("social_stream_post_kanban_view", StreamPostKanbanView);
