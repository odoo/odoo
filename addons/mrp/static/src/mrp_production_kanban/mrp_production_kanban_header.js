import { _t } from "@web/core/l10n/translation";
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { MrpProductionColumnProgress } from "./mrp_production_kanban_column_progress";

export class MrpProductionKanbanHeader extends KanbanHeader {
    static components = {
        ...KanbanHeader.components,
        ColumnProgress: MrpProductionColumnProgress,
    };
    get groupAggregate() {
        const value = this.props.group.list.records.reduce(
            (sum, record) => sum + record.data.remaining_time,
            0
        );
        return { value, title: _t("Total Remaining Time")};
    }
}
