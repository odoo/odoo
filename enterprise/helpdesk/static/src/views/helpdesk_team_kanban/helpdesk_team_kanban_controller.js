/** @odoo-module **/

import { KanbanController } from '@web/views/kanban/kanban_controller';
import { HelpdeskTeamDashboard } from '@helpdesk/components/helpdesk_team_dashboard/helpdesk_team_dashboard';

export class HelpdeskTeamKanbanController extends KanbanController {
    static template = "helpdesk.HelpdeskTeamKanbanView";
    static components = {
        ...KanbanController.components,
        HelpdeskTeamDashboard,
    };
}
