import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export function makeAwaitable(dialog, comp, props, options) {
    return new Promise((resolve) => {
        dialog.add(
            comp,
            {
                ...props,
                getPayload: (response) => {
                    resolve(response);
                },
            },
            {
                ...options,
                onClose: () => resolve(),
            }
        );
    });
}

export function makeActionAwaitable(action, config, additionalArgs) {
    return new Promise((resolve) => {
        action.doAction(config, {
            ...additionalArgs,
            props: {
                ...additionalArgs?.props,
                onSave: (record) => {
                    action.doAction({
                        type: "ir.actions.act_window_close",
                    });
                    resolve(record);
                },
            },
        });
    });
}

export function ask(dialog, props, options, comp = ConfirmationDialog) {
    return new Promise((resolve) => {
        dialog.add(
            comp,
            {
                ...props,
                confirm: () => resolve(true),
                cancel: () => resolve(false),
            },
            {
                ...options,
                onClose: () => resolve(false),
            }
        );
    });
}
