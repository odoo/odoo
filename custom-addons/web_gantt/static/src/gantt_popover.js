/** @odoo-module **/

import { Component } from "@odoo/owl";

export class GanttPopover extends Component {
    onClick() {
        this.props.button.onClick();
        this.props.close();
    }
}
GanttPopover.template = "web_gantt.GanttPopover";
GanttPopover.props = ["title", "template?", "context", "close", "button?"];
GanttPopover.defaultProps = { template: "web_gantt.GanttPopover.default" };
