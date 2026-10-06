import { Plugin, providePlugins, useConfig, usePlugin, useScope } from "@odoo/owl";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { evaluateExpr } from "@web/core/py_js/py";
import { useService } from "@web/core/utils/hooks";
import { useEnv } from "@web/owl2/utils";
import { getUploadOptions, pickFiles, uploadFiles } from "@web/views/view_button/upload_button";

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
 * @property {Function} [beforeExecuteAction] called with the click params and `{ files }` for an
 *      upload button; returns false to cancel the action (e.g. to upload the files in its own way)
 * @property {Function} [reload]
 */

/**
 * @typedef {{
 *  clickParams: any;
 *  getResParams(): any;
 *  beforeExecute?(): Promise<void | boolean>;
 *  newWindow?: boolean;
 *  files?: File[]; // upload buttons: the files to upload (e.g. dropped), asked to the user if missing
 * }} ViewButtonHandlerParams
 * @typedef {(params: ViewButtonHandlerParams) => (void | Promise<void>)} ViewButtonHandler
 */

class ViewButtonPlugin extends Plugin {
    handler = useConfig("handler");
}

/**
 * @param {ViewButtonHandler} handler
 */
export function provideViewButtonHandler(handler) {
    providePlugins([ViewButtonPlugin], { handler });
}

/**
 * @returns {ViewButtonHandler}
 */
export function useViewButtonHandler() {
    return usePlugin(ViewButtonPlugin).handler;
}

/**
 * @param {() => HTMLElement | null} ref the container signal ref
 * @param {Options} [options={}]
 */
export function useViewButtons(ref, options = {}) {
    const action = useService("action");
    const dialog = useService("dialog");
    const scope = useScope();
    const env = useEnv();

    // Resolved lazily: the element only exists once the component is mounted.
    const getRefEl = () => ref?.() ?? null;
    async function onClickViewButton({
        clickParams,
        getResParams,
        beforeExecute,
        newWindow,
        files,
    }) {
        const isUpload = clickParams.type === "upload";
        if (isUpload && !files) {
            // Asked first, while the browser still considers the click as a user gesture
            files = await pickFiles(getUploadOptions(clickParams));
            if (!files.length) {
                return;
            }
        }
        async function execute() {
            let _continue = true;
            if (beforeExecute) {
                _continue = undefinedAsTrue(await beforeExecute());
            }

            _continue =
                _continue &&
                undefinedAsTrue(await options.beforeExecuteAction?.(clickParams, { files }));
            if (!_continue) {
                return;
            }
            const closeDialog = (clickParams.close || clickParams.special) && env.dialogData?.close;
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
                    if (!closeDialog && !scope.isDestroyed() && !onCloseInfo?.noReload) {
                        await options.reload?.();
                    }
                },
            });
            let error;
            try {
                if (isUpload) {
                    const { model } = getUploadOptions(clickParams);
                    const result = await uploadFiles(env.services, {
                        clickParams,
                        resModel: model || params.resModel,
                        resIds: model ? [] : params.resId ? [params.resId] : params.resIds,
                        context: Object.assign({}, params.context, buttonContext),
                        files,
                    });
                    if (result) {
                        await action.doAction(result, { onClose: doActionParams.onClose });
                    } else if (result !== null) {
                        await doActionParams.onClose();
                    }
                } else {
                    await action.doActionButton(doActionParams, { newWindow });
                }
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
    }
    provideViewButtonHandler(onClickViewButton);

    function getEl() {
        const el = getRefEl();
        if (env.inDialog) {
            return el ? el.closest(".modal") : null;
        } else {
            return el;
        }
    }

    return onClickViewButton;
}
