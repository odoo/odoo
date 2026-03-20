import { kanbanView } from '@web/views/kanban/kanban_view';
import { registry } from '@web/core/registry';
import { TimeOffKanbanRenderer } from './kanban_renderer';
import { TimeOffKanbanController } from './kanban_controller';

const TimeOffKanbanView = {
    ...kanbanView,
    Renderer: TimeOffKanbanRenderer,
    Controller: TimeOffKanbanController
}

registry.category('views').add('time_off_kanban_dashboard', TimeOffKanbanView);
