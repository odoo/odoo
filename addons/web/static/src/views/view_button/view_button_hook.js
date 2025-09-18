// @ts-check

/** @module @web/views/view_button/view_button_hook - Hook wiring view button click handling with confirmation dialogs and UI blocking */

import { status, useComponent, useEnv, useSubEnv } from "@odoo/owl";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/ui/dialog/confirmation_dialog";

/**
 * Disable all buttons within `el` (and overlays) while executing `fct`, then re-enable them.
 * Prevents double-clicks during async button actions.
 * @param {HTMLElement | null} el - container whose buttons are disabled
 * @param {() => Promise<any>} fct - async callback to execute
 * @returns {Promise<any>}
 */
export async function executeButtonCallback(el, fct) {
    let btns = [];
    function disableButtons() {
        btns = [
            ...btns,
            ...el.querySelectorAll("button:not([disabled])"),
            ...document.querySelectorAll(".o-overlay-container button:not([disabled])"),
        ];
        for (const btn of btns) {
            btn.setAttribute("disabled", "1");
        }
    }

    function enableButtons() {
        for (const btn of btns) {
            btn.removeAttribute("disabled");
        }
    }

    disableButtons();
    let res;
    try {
        res = await fct();
    } finally {
        enableButtons();
    }
    return res;
}

function undefinedAsTrue(val) {
    return val === undefined || val;
}

/**
 * @typedef {Object} ViewButtonsOptions
 * @property {Function} [afterExecuteAction] - called after the button action completes
 * @property {Function} [beforeExecuteAction] - called before the button action; return false to abort
 * @property {Function} [reload] - called to reload the view after a non-dialog action
 */

/**
 * OWL hook that injects `onClickViewButton` into the sub-environment, wiring up
 * confirmation dialogs, context evaluation, button disabling, and action execution
 * for all ViewButton descendants.
 * @param {{ readonly el: HTMLElement | null; }} ref - component root ref
 * @param {ViewButtonsOptions} [options={}]
 */
export function useViewButtons(ref, options = {}) {
    const action = useService("action");
    const dialog = useService("dialog");
    const comp = useComponent();
    const env = useEnv();
    useSubEnv({
        async onClickViewButton({
            clickParams,
            getResParams,
            beforeExecute,
            newWindow,
        }) {
            async function execute() {
                let _continue = true;
                if (beforeExecute) {
                    _continue = undefinedAsTrue(await beforeExecute());
                }

                _continue =
                    _continue &&
                    undefinedAsTrue(await options.beforeExecuteAction?.(clickParams));
                if (!_continue) {
                    return;
                }
                const closeDialog =
                    (clickParams.close || clickParams.special) && env.dialogData?.close;
                const params = getResParams();
                let buttonContext = {};
                if (clickParams.context) {
                    if (typeof clickParams.context === "string") {
                        buttonContext = evaluateExpr(
                            clickParams.context,
                            params.evalContext,
                        );
                    } else {
                        buttonContext = clickParams.context;
                    }
                }
                if (clickParams.buttonContext) {
                    Object.assign(buttonContext, clickParams.buttonContext);
                }
                const doActionParams = {
                    ...clickParams,
                    resModel: params.resModel,
                    resId: params.resId,
                    resIds: params.resIds,
                    context: params.context || {},
                    buttonContext,
                    onClose: async (onCloseInfo) => {
                        if (
                            !closeDialog &&
                            status(comp) !== "destroyed" &&
                            !onCloseInfo?.noReload
                        ) {
                            await options.reload?.();
                        }
                    },
                };
                let error;
                try {
                    await action.doActionButton(doActionParams, { newWindow });
                } catch (_e) {
                    error = _e;
                }
                await options.afterExecuteAction?.(clickParams);
                if (closeDialog) {
                    closeDialog();
                }
                if (error) {
                    return Promise.reject(error);
                }
            }

            if (clickParams.confirm) {
                return executeButtonCallback(getEl(), async () => {
                    await new Promise((resolve) => {
                        const dialogProps = {
                            ...(clickParams["confirm-title"] && {
                                title: clickParams["confirm-title"],
                            }),
                            ...(clickParams["confirm-label"] && {
                                confirmLabel: clickParams["confirm-label"],
                            }),
                            ...(clickParams["cancel-label"] && {
                                cancelLabel: clickParams["cancel-label"],
                            }),
                            body: clickParams.confirm,
                            confirm: () => execute(),
                            cancel: () => {},
                        };
                        dialog.add(ConfirmationDialog, dialogProps, {
                            onClose: /** @type {any} */ (resolve),
                        });
                    });
                });
            } else {
                return executeButtonCallback(getEl(), execute);
            }
        },
    });

    function getEl() {
        if (env.inDialog) {
            const el = ref.el;
            return el ? el.closest(".modal") : null;
        } else {
            return ref.el;
        }
    }
}

const sharedComponents = registry.category("shared_components");
sharedComponents.add("executeButtonCallback", executeButtonCallback);
sharedComponents.add("useViewButtons", useViewButtons);
