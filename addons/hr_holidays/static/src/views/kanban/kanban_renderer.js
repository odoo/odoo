import { KanbanRenderer } from '@web/views/kanban/kanban_renderer';
import { TimeOffDashboard } from '../../dashboard/time_off_dashboard';

export class TimeOffKanbanRenderer extends KanbanRenderer {
    static template = "hr_holidays.KanbanRenderer";
    static components = {
        ...TimeOffKanbanRenderer.components,
        TimeOffDashboard,
    };
    get employeeId() {
        return this.env.model.config.context.active_id || null;
    }

    get showDashboard() {
        return this.env.model.config.context.show_dashboard || false;
    }
}
