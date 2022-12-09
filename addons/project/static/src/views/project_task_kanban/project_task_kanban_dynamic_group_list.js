/** @odoo-module */

import { session } from '@web/session';
import { ProjectTaskKanbanDynamicGroupList as NoteBaseGroupListClass} from '@note/views/project_task_kanban/project_task_kanban_dynamic_group_list';
import { ProjectTaskKanbanModel } from '@note/views/project_task_kanban/project_task_kanban_model';

export class ProjectTaskKanbanDynamicGroupList extends NoteBaseGroupListClass {
    get additional_kanban_domain() {
        return ['|',
                '&', ['is_todo', '=', true], '|', ['user_id', '=', session.uid], ['message_partner_ids', '=', this.model.user.partnerId],
                '&', ['is_todo', '=', false], ['user_ids', 'in', session.uid]];
    }
}

ProjectTaskKanbanModel.DynamicGroupList = ProjectTaskKanbanDynamicGroupList;
