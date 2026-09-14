/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { ConfirmationDialog } from "@web/ui/dialog";
const log = makeLogger("pos.dialog");
export function makeAwaitable(dialog, comp, props, options) {
    const endDialog = log.perf(`makeAwaitable ${comp.name}`);
    log.lifecycle("makeAwaitable: open", () => ({ component: comp.name }));
    return new Promise((resolve, reject) => {
        dialog.add(
            comp,
            { ...props, getPayload: resolve },
            { ...options, onClose: closeWithCleanup(options, () => resolve(), reject) },
        );
    }).finally(() => endDialog({ component: comp.name }));
}

// Return cleanup failures to the dialog service as well as the pending caller.
function closeWithCleanup(options, resolve, reject) {
    return async (...args) => {
        try {
            await options?.onClose?.(...args);
            resolve();
        } catch (error) {
            reject(error);
            throw error;
        }
    };
}

export function makeActionAwaitable(action, config, additionalArgs) {
    const endAction = log.perf(`makeActionAwaitable ${config}`);
    log.lifecycle("makeActionAwaitable: open", () => ({
        action: config,
        resId: additionalArgs?.props?.resId,
    }));
    let savedRecord;
    return new Promise((resolve, reject) => {
        Promise.resolve(
            action.doAction(config, {
                ...additionalArgs,
                onClose: async (...args) => {
                    try {
                        await additionalArgs?.onClose?.(...args);
                        log.lifecycle("makeActionAwaitable: close callback", () => ({
                            action: config,
                            saving: Boolean(savedRecord),
                        }));
                        if (!savedRecord) {
                            resolve();
                        }
                    } catch (error) {
                        reject(error);
                    }
                },
                props: {
                    ...additionalArgs?.props,
                    onSave: async (record) => {
                        savedRecord = record;
                        try {
                            await action.doAction({
                                type: "ir.actions.act_window_close",
                            });
                            resolve(record);
                        } catch (error) {
                            reject(error);
                        }
                    },
                },
            }),
        ).catch(reject);
    }).finally(() => endAction({ action: config, saved: savedRecord?.resId }));
}

export function ask(dialog, props, options, comp = ConfirmationDialog) {
    log.lifecycle("ask: open", () => ({ component: comp.name, title: props?.title }));
    return new Promise((resolve, reject) => {
        const answer = (value, how) => {
            log.logic("ask: answered", () => ({
                component: comp.name,
                title: props?.title,
                how,
                value,
            }));
            resolve(value);
        };
        dialog.add(
            comp,
            {
                ...props,
                confirm: () => answer(true, "confirm"),
                cancel: () => answer(false, "cancel"),
            },
            {
                ...options,
                onClose: closeWithCleanup(
                    options,
                    () => answer(false, "close"),
                    reject,
                ),
            },
        );
    });
}
