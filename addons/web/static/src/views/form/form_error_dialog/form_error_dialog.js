import { Dialog } from "@web/core/dialog/dialog";

import { Component } from "@odoo/owl";

export class FormErrorDialog extends Component {
    static template = "web.FormErrorDialog";
    static components = { Dialog };
    static props = {
        message: { type: String, optional: true },
        onDiscard: Function,
        onStayHere: Function,
        close: Function,
    };
    async discard() {
        await this.props.onDiscard();
        this.props.close();
    }

    async stay() {
        await this.props.onStayHere();
        this.props.close();
    }
}
