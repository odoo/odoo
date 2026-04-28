/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { MrpWorkorderKanbanHeader } from "./mrp_workorder_kanban_header";
import { MrpWorkorderKanbanRecord } from "./mrp_workorder_kanban_record";

export class MrpWorkorderKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        KanbanHeader: MrpWorkorderKanbanHeader,
        KanbanRecord: MrpWorkorderKanbanRecord,
    };

    async sortRecordDrop(dataRecordId, dataGroupId, params) {
        // After a resequence, some workorder of other workcenter may have their planned date changed,
        // so we need to reload all the kanban cards.
        await super.sortRecordDrop(dataRecordId, dataGroupId, params);
        await this.props.list.model.load();
    }
}
