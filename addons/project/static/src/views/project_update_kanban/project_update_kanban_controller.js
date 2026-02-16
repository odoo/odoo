import { KanbanController } from '@web/views/kanban/kanban_controller';

export class ProjectUpdateKanbanController extends KanbanController {
    get className() {
        return super.className + ' o_updates_controller';
    }
}
