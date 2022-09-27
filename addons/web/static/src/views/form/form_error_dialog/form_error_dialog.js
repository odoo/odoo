/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { RPCError } from "@web/core/network/rpc_service";
import { registry } from "@web/core/registry";

const { Component, onWillDestroy } = owl;

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
}
FormErrorDialog.template = "web.FormErrorDialog";
FormErrorDialog.components = { Dialog };

function makeFormErrorHandler(onDiscard) {
    return (env, error, originalError) => {
        if (
            originalError &&
            originalError.legacy &&
            originalError.message &&
            originalError.message instanceof RPCError
        ) {
            const event = originalError.event;
            originalError = originalError.message;
            error.unhandledRejectionEvent.preventDefault();
            if (event.isDefaultPrevented()) {
                // in theory, here, event was already handled
                return true;
            }
            event.preventDefault();

            env.services.dialog.add(FormErrorDialog, {
                message: originalError.message,
                data: originalError.data,
                onDiscard,
            });

            return true;
        }
        return false;
    };
}

let formId = 0;

export function useFormErrorDialog(onDiscard) {
    const errorHandlerKey = `form_error_handler_${++formId}`;
    registry
        .category("error_handlers")
        .add(errorHandlerKey, makeFormErrorHandler(onDiscard), { sequence: 0 });
    onWillDestroy(() => {
        registry.category("error_handlers").remove(errorHandlerKey);
    });
}
