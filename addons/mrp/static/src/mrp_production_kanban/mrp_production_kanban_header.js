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
      (sum, record) => sum + Math.max(0, record.data.remaining_time),
      0,
    );
    return { value, title: _t("Total Remaining Time") };
  }

  canQuickCreate() {
    const allowedGroupByFields = ["product_id"];
    const currentGroupByField = this.props.list.groupByField?.name;
    if (
      currentGroupByField === "date_start" &&
      this.props.list.groupBy[0] === "date_start:day"
    ) {
      return true;
    }
    return allowedGroupByFields.includes(this.props.list.groupByField.name);
  }
}
