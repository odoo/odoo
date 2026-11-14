/** @odoo-module **/

export class GanttArchParser {
    parse(arch, relatedModels, resModel) {
        const archInfo = {
            dateStart: arch.getAttribute("date_start") || "start_datetime",
            dateStop: arch.getAttribute("date_stop") || "end_datetime",
            defaultGroupBy: arch.getAttribute("default_group_by") || "resource_id",
            defaultScale: arch.getAttribute("default_scale") || arch.getAttribute("scale") || "week",
            colorField: arch.getAttribute("color") || "color",
            string: arch.getAttribute("string") || "Schedule by Resource",
        };
        return archInfo;
    }
}
