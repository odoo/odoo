import { _t } from "@web/core/l10n/translation";
import { KanbanHeader } from "@web/views/kanban/kanban_header";
import { MrpProductionColumnProgress } from "./mrp_production_kanban_column_progress";

export class MrpProductionKanbanHeader extends KanbanHeader {
    static template = "mrp.MrpProductionKanbanHeader";
    static components = {
        ...KanbanHeader.components,
        ColumnProgress: MrpProductionColumnProgress,
    };
    get groupAggregate() {
        const value = this.props.group.list.records.reduce(
            (sum, record) => sum + Math.max(0, record.data.remaining_time),
            0
        );
        return { value, title: _t("Total Remaining Time")};
    }

    get columnTitle() {
        const group = this.props.group;
        let title = group.displayName;
        if (group.value && typeof group.value === "object" && typeof group.value.startOf === "function" && title.includes("W")) {
            const start = group.value.startOf("week").toFormat("dd/MM");
            const end = group.value.endOf("week").toFormat("dd/MM");
            title = `${title} (${start}-${end})`;
        }
        return title;
    }
}
