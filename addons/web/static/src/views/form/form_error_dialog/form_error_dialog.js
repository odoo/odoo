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
<<<<<<< HEAD
||||||| parent of f869443be7d2 (temp)

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
=======

function formSaveErrorHandler(env, error, originalError) {
    if (originalError && originalError.__raisedOnFormSave) {
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
>>>>>>> f869443be7d2 (temp)
