/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { View } from "@web/views/view";
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

/**
 * The schedule board is exposed as a client action. A client action receives
 * action props only (no `archInfo`/`resModel`), so it must render the gantt
 * view through the standard `View` component to get the view props, the
 * search model and the action/domain wiring.
 */
export class ScheduleGanttAction extends Component {
    static template = "school_management.ScheduleGanttAction";
    static components = { View };
    static props = {
        action: Object,
        actionId: { type: Number, optional: true },
        className: { type: String, optional: true },
        "*": true,
    };

    setup() {
        this.viewProps = {
            resModel: "university.timetable.slot",
            type: "gantt",
            views: [
                [false, "gantt"],
                [false, "search"],
            ],
            context: this.props.action.context || {},
        };
    }
}

registry.category("actions").add("university_schedule_gantt", ScheduleGanttAction);
registry.category("actions").add("university_schedule_view", ScheduleGanttAction);
