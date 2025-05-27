import { extractAttributes } from "@web/core/utils/xml";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";

export class RottingKanbanArchParser extends KanbanArchParser {
    /**
     * @override
     */
    parseProgressBar(progressBar, fields) {
        const result = super.parseProgressBar(...arguments);
        const attrs = extractAttributes(progressBar, ["rotting_count_field"]);
        result.rotting_count_field = fields[attrs.rotting_count_field] || false;
        return result;
    }
}
