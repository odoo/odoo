import { extractAttributes } from "@web/core/utils/xml";
import { RottingKanbanArchParser } from "@mail/js/rotting_mixin/rotting_kanban_arch_parser";

export class CrmKanbanArchParser extends RottingKanbanArchParser {
    /**
     * @override
     */
    parseProgressBar(progressBar, fields) {
        const result = super.parseProgressBar(...arguments);
        const attrs = extractAttributes(progressBar, ["recurring_revenue_sum_field"]);
        result.recurring_revenue_sum_field = fields[attrs.recurring_revenue_sum_field] || false;
        return result;
    }
}
