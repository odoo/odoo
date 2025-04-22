import { useService } from "@web/core/utils/hooks";
import { evaluateExpr } from "@web/core/py_js/py";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { status, useComponent, useEnv, useSubEnv } from "@odoo/owl";

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
    return typeof val === "undefined" || val;
}

/**
 * @typedef {Object} Options
 * @property {Function} [afterExecuteAction]
 * @property {Function} [beforeExecuteAction]
 * @property {Function} [reload]
 */

/**
 * @param {{ readonly el: HTMLElement | null; }} ref
 * @param {Options} [options={}]
 */
export function useViewButtons(ref, options = {}) {
    const action = useService("action");
    const dialog = useService("dialog");
    const comp = useComponent();
    const env = useEnv();
    useSubEnv({
        async onClickViewButton({ clickParams, getResParams, beforeExecute }) {
            async function execute() {
                let _continue = true;
                if (beforeExecute) {
                    _continue = undefinedAsTrue(await beforeExecute());
                }

                _continue =
                    _continue && undefinedAsTrue(await options.beforeExecuteAction?.(clickParams));
                if (!_continue) {
                    return;
                }
                const closeDialog =
                    (clickParams.close || clickParams.special) && env.dialogData?.close;
                const params = getResParams();
                let buttonContext = {};
                if (clickParams.context) {
                    if (typeof clickParams.context === "string") {
                        buttonContext = evaluateExpr(clickParams.context, params.evalContext);
                    } else {
                        buttonContext = clickParams.context;
                    }
                }
                if (clickParams.buttonContext) {
                    Object.assign(buttonContext, clickParams.buttonContext);
                }
                const doActionParams = Object.assign({}, clickParams, {
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
                });
                let error;
                try {
                    await action.doActionButton(doActionParams);
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
                executeButtonCallback(getEl(), async () => {
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
                        dialog.add(ConfirmationDialog, dialogProps, { onClose: resolve });
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
