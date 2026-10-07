import { CrmColumnProgress } from "./crm_column_progress";
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
    };

    // Setup to disable the default group by stage id
    setup(){
        super.setup();
        if(this.env.services.ui.isSmall){
            this.env.searchModel.defaultGroupBy = [];
        }
    }
}
