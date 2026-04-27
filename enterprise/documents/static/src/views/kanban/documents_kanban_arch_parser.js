import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";

export class DocumentsKanbanArchParser extends KanbanArchParser {
    parse(xmlDoc, models, modelName) {
        const archInfo = super.parse(xmlDoc, models, modelName);
        archInfo.canOpenRecords = false;
        return archInfo;
    }
}
