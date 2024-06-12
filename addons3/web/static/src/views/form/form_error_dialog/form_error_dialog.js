/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";

import { Component } from "@odoo/owl";

export class FormErrorDialog extends Component {
    async discard() {
        await this.props.onDiscard();
        this.props.close();
    }

    async stay() {
        await this.props.onStayHere();
        this.props.close();
    }
}
FormErrorDialog.template = "web.FormErrorDialog";
FormErrorDialog.components = { Dialog };
