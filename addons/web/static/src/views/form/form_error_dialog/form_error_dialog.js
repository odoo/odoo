/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";

import { Component } from "@odoo/owl";
const errorHandlerRegistry = registry.category("error_handlers");

export class FormErrorDialog extends Component {
    setup() {
        const { data, message } = this.props;
        if (data && data.arguments && data.arguments.length > 0) {
            this.message = data.arguments[0];
        } else {
            this.message = message;
        }
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

function formSaveErrorHandler(env, error, originalError) {
    if (originalError.__raisedOnFormSave) {
        const event = originalError.event;
        error.unhandledRejectionEvent.preventDefault();
        if (event.isDefaultPrevented()) {
            // in theory, here, event was already handled
            return true;
        }
        event.preventDefault();

        env.services.dialog.add(
            FormErrorDialog,
            {
                message: originalError.message.message,
                data: originalError.message.data,
                onDiscard: originalError.onDiscard,
                onStayHere: originalError.onStayHere,
            },
            {
                onClose: originalError.onStayHere,
            }
        );

        return true;
    }
}
errorHandlerRegistry.add("formSaveErrorHandler", formSaveErrorHandler);
