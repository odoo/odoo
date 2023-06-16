/** @odoo-module */

import { KanbanModel } from "@web/views/kanban/kanban_model";

import { ProjectTaskKanbanDynamicGroupList } from "./project_task_kanban_dynamic_group_list";
import { Record } from '@web/views/relational_model';

export class ProjectTaskKanbanModel extends KanbanModel { }

ProjectTaskKanbanModel.DynamicGroupList = ProjectTaskKanbanDynamicGroupList;
