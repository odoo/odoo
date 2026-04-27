import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class GanttPopoverInDialog extends Component {
    static components = { Dialog };
    static props = ["close", "component", "componentProps", "dialogTitle"];
    static template = "web_gantt.GanttPopoverInDialog";
    get componentProps() {
        return { ...this.props.componentProps, close: this.props.close };
    }
}
