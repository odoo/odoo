/** @odoo-module **/

import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { extractAttributes } from "@web/core/utils/xml";

export class CrmKanbanArchParser extends KanbanArchParser {
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
