import { CrmColumnProgress } from "./crm_column_progress";
import { RottingKanbanRecord } from "@mail/js/rotting_mixin/rotting_kanban_record";
import { RottingKanbanHeader } from "@mail/js/rotting_mixin/rotting_kanban_header";
import { RottingKanbanRenderer } from "@mail/js/rotting_mixin/rotting_kanban_renderer";

class CrmKanbanHeader extends RottingKanbanHeader {
    static components = {
        ...RottingKanbanHeader.components,
        ColumnProgress: CrmColumnProgress,
    };
}

export class CrmKanbanRenderer extends RottingKanbanRenderer {
    static components = {
        ...RottingKanbanRenderer.components,
        KanbanHeader: CrmKanbanHeader,
        KanbanRecord: RottingKanbanRecord,
    };
}
