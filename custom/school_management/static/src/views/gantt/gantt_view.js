/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { GanttController } from "./gantt_controller";
import { GanttArchParser } from "./gantt_arch_parser";
import { GanttModel } from "./gantt_model";
import { GanttRenderer } from "./gantt_renderer";

if (session.view_info && !session.view_info.gantt) {
    session.view_info.gantt = {
        icon: "fa fa-tasks",
        multi_record: true,
        multiRecord: true,
        display_name: "Gantt",
        type: "gantt",
    };
}

export const ganttView = {
    type: "gantt",
    display_name: "Gantt",
    icon: "fa fa-tasks",
    multiRecord: true,
    searchMenuTypes: ["filter", "groupBy", "favorite"],

    ArchParser: GanttArchParser,
    Controller: GanttController,
    Model: GanttModel,
    Renderer: GanttRenderer,

    props: (genericProps, view) => {
        const { ArchParser } = view;
        const { arch, relatedModels, resModel } = genericProps;
        const archInfo = new ArchParser().parse(arch || document.createElement("gantt"), relatedModels, resModel);
        return {
            ...genericProps,
            archInfo,
            Model: view.Model,
            Renderer: view.Renderer,
        };
    },
};

if (!registry.category("views").contains("gantt")) {
    registry.category("views").add("gantt", ganttView);
}
registry.category("actions").add("university_schedule_gantt", GanttController);
registry.category("actions").add("university_schedule_view", GanttController);
