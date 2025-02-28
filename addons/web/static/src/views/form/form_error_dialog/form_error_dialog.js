/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

export class FormErrorDialog extends Component {
    setup() {
        this.action = useService("action");
    }

    get additional_button() {
        if (this.props.data.name === "odoo.exceptions.RedirectWarning") {
            return {
                name: this.props.data.arguments[2],
                callback: () => this.action.doAction(this.props.data.arguments[1]),
            };
        }
        return null;
    }

    get message() {
        if (this.props.data.name === "odoo.exceptions.RedirectWarning") {
            return this.props.data.arguments[0];
        }
        return this.props.message;
    }

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
