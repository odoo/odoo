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

export function ask(dialog, props, options, comp = ConfirmationDialog) {
    return new Promise((resolve) => {
        dialog.add(
            comp,
            {
                ...props,
                confirm: props.confirm ? async ()=>{return await props.confirm()} : () => resolve(true),
                cancel: props.cancel? async()=>{return await props.cancel()} : () => resolve(false),
            },
            {
                ...options,
                onClose: () => resolve(false),
            }
        );
    });
}
