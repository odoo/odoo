/** @odoo-module **/

import { GanttPopover } from "@web_gantt/gantt_popover";

export class TaskGanttPopover extends GanttPopover {
    static template = "project_enterprise.GanttPopover";
    static props = [
        ...GanttPopover.props,
        'unschedule',
    ];

    onClickUnschedule() {
        this.props.unschedule();
        this.props.close();
    }
}
