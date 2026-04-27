import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { HelpdeskTeamKanbanController } from './helpdesk_team_kanban_controller';

export const HelpdeskTeamKanbanView = {
    ...kanbanView,
    Controller: HelpdeskTeamKanbanController,
    searchview_hidden: true,
};

registry.category('views').add('helpdesk_team_kanban_view', HelpdeskTeamKanbanView);
