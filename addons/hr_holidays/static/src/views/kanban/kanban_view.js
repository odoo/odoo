import { kanbanView } from '@web/views/kanban/kanban_view';
import { registry } from '@web/core/registry';
import { HrHolidaysSearchModel } from '@hr_holidays/search/hr_holidays_search_model';
import { TimeOffKanbanRenderer } from './kanban_renderer';
import { TimeOffKanbanController } from './kanban_controller';

const TimeOffKanbanView = {
    ...kanbanView,
    Renderer: TimeOffKanbanRenderer,
    Controller: TimeOffKanbanController,
    SearchModel: HrHolidaysSearchModel,
}

registry.category('views').add('time_off_kanban_dashboard', TimeOffKanbanView);
