import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class PopoverInDialog extends Component {
    static components = { Dialog };
    static props = ["close", "component", "componentProps", "dialogTitle"];
    static template = "web.PopoverInDialog";
    get componentProps() {
        return { ...this.props.componentProps, close: this.props.close };
    }
}
