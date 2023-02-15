/** @odoo-module **/

import { CrmColumnProgress } from "./crm_column_progress";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

export class CrmKanbanRenderer extends KanbanRenderer {}
CrmKanbanRenderer.template = "crm.CrmKanbanRenderer";
CrmKanbanRenderer.components = {
    ...KanbanRenderer.components,
    CrmColumnProgress,
};
