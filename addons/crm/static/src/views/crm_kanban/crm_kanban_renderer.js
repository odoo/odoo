/** @odoo-module **/

import { CrmColumnProgress } from "./crm_column_progress";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { KanbanHeader } from "@web/views/kanban/kanban_header";

class CrmKanbanHeader extends KanbanHeader {
    static template = "crm.CrmKanbanHeader";
    static components = {
        ...KanbanHeader.components,
        ColumnProgress: CrmColumnProgress,
    };
}

export class CrmKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanHeader: CrmKanbanHeader,
    };
}
