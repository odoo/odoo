/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { evaluateExpr } from "@web/core/py_js/py";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

import { status, useEnv, useSubEnv } from "@odoo/owl";

function disableButtons(el) {
    // WOWL: can we do this non-imperatively?
    const btns = [...el.querySelectorAll("button:not([disabled])")];
    for (const btn of btns) {
        btn.setAttribute("disabled", "1");
    }
    return btns;
}

function enableButtons(el, manuallyDisabledButtons, enableAction) {
    if (el) {
        for (const btn of manuallyDisabledButtons) {
            btn.removeAttribute("disabled");
        }
    }
    if (enableAction) {
        enableAction();
    }
}

function undefinedAsTrue(val) {
    return typeof val === "undefined" || val;
}
export function useViewButtons(model, ref, options = {}) {
    const action = useService("action");
    const dialog = useService("dialog");
    const comp = owl.useComponent();
    const env = useEnv();
    const beforeExecuteAction =
        options.beforeExecuteAction ||
        (() => {
            return true;
        });
    const afterExecuteAction = options.afterExecuteAction || (() => {});
    useSubEnv({
        async onClickViewButton({
            clickParams,
            getResParams,
            beforeExecute,
            disableAction,
            enableAction,
        }) {
            const manuallyDisabledButtons = disableButtons(getEl());
            if (disableAction) {
                disableAction();
            }

            async function execute() {
                let _continue = true;
                if (beforeExecute) {
                    _continue = undefinedAsTrue(await beforeExecute());
                }

                _continue = _continue && undefinedAsTrue(await beforeExecuteAction(clickParams));
                if (!_continue) {
                    enableButtons(getEl(), manuallyDisabledButtons, enableAction);
                    return;
                }
                const closeDialog = clickParams.close && env.closeDialog;
                const params = getResParams();
                const resId = params.resId;
                const resIds = params.resIds || model.resIds;
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
                    resModel: params.resModel || model.resModel,
                    resId,
                    resIds,
                    context: params.context || {}, //LPE FIXME new Context(payload.env.context).eval();
                    buttonContext,
                    onClose: async () => {
                        if (!closeDialog && status(comp) !== "destroyed") {
                            const reload = options.reload || (() => model.root.load());
                            await reload();
                            comp.render(true); // FIXME WOWL reactivity
                        }
                    },
                });
                let error;
                try {
                    await action.doActionButton(doActionParams);
                } catch (_e) {
                    error = _e;
                    await doActionParams.onClose();
                }
                await afterExecuteAction(clickParams);
                if (closeDialog) {
                    closeDialog();
                }
                enableButtons(getEl(), manuallyDisabledButtons, enableAction);
                if (error) {
                    return Promise.reject(error);
                }
            }

            if (clickParams.confirm) {
                await new Promise((resolve) => {
                    const dialogProps = {
                        body: clickParams.confirm,
                        confirm: execute,
                        cancel: () => {},
                    };
                    dialog.add(ConfirmationDialog, dialogProps, { onClose: resolve });
                });
                enableButtons(getEl(), manuallyDisabledButtons, enableAction);
            } else {
                return execute();
            }
        },
    });

    function getEl() {
        if (env.inDialog) {
            return ref.el.closest(".modal");
        } else {
            return ref.el;
        }
    }
}
