/** @odoo-module native */
import { KanbanArchParser } from "@web/views/kanban";

export class CrmKanbanArchParser extends KanbanArchParser {
    parseProgressBar(progressBar, fields) {
        const result = super.parseProgressBar(...arguments);
        const { recurring_revenue_sum_field } = progressBar.attrs || {};
        result.recurring_revenue_sum_field =
            fields[recurring_revenue_sum_field] || false;
        return result;
    }
}
