import { ColumnProgress } from "@web/views/view_components/column_progress";
import { MrpProductionAnimatedNumber } from "./mrp_production_kanban_animated_number";

export class MrpProductionColumnProgress extends ColumnProgress {
    static components = {
        ...ColumnProgress.components,
        AnimatedNumber: MrpProductionAnimatedNumber,
    };
}
