/** @odoo-module **/

import { GanttArchParser } from "@web_gantt/gantt_arch_parser";

export class TaskGanttArchParser extends GanttArchParser {
    parse() {
        const archInfo = super.parse(...arguments);
        const decorationFields = new Set([...archInfo.decorationFields, "project_id"]);
        if (archInfo.dependencyEnabled) {
            decorationFields.add("allow_task_dependencies");
            decorationFields.add("display_warning_dependency_in_gantt");
        }
        return {
            ...archInfo,
            decorationFields: [...decorationFields],
        };
    }
}
