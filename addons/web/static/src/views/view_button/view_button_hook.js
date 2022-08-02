/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { evaluateExpr } from "@web/core/py_js/py";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const { useEnv, useSubEnv } = owl;

function disableButtons(el) {
    // WOWL: can we do this non-imperatively?
    const btns = [...el.querySelectorAll("button:not([disabled])")];
    for (const btn of btns) {
        btn.setAttribute("disabled", "1");
    }
    return btns;
}

function enableButtons(el, manuallyDisabledButtons) {
    if (el) {
        for (const btn of manuallyDisabledButtons) {
            btn.removeAttribute("disabled");
        }
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
    useSubEnv({
        async onClickViewButton({ clickParams, record, beforeExecute }) {
            const manuallyDisabledButtons = disableButtons(getEl());

            async function execute() {
                let _continue = true;
                if (beforeExecute) {
                    _continue = undefinedAsTrue(await beforeExecute());
                }

                _continue = _continue && undefinedAsTrue(await beforeExecuteAction(clickParams));
                if (!_continue) {
                    enableButtons(getEl(), manuallyDisabledButtons);
                    return;
                }
                const resId = record.resId;
                const resIds = record.resIds || model.resIds;
                let buttonContext = {};
                if (clickParams.context) {
                    if (typeof clickParams.context === "string") {
                        const valuesForEval = Object.assign({}, record.data, {
                            active_id: resId,
                            active_ids: resIds,
                        });
                        buttonContext = evaluateExpr(clickParams.context, valuesForEval);
                    } else {
                        buttonContext = clickParams.context;
                    }
                }
                if (clickParams.buttonContext) {
                    Object.assign(buttonContext, clickParams.buttonContext);
                }
                const doActionParams = Object.assign({}, clickParams, {
                    resModel: record.resModel || model.resModel,
                    resId,
                    resIds,
                    context: record.context || {}, //LPE FIXME new Context(payload.env.context).eval();
                    buttonContext,
                    onClose: async () => {
                        const reload = options.reload || (() => record.model.root.load());
                        await reload();
                        comp.render(true); // FIXME WOWL reactivity
                    },
                });
                let error;
                try {
                    await action.doActionButton(doActionParams);
                } catch (_e) {
                    error = _e;
                    await doActionParams.onClose();
                }
                enableButtons(getEl(), manuallyDisabledButtons);
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
                enableButtons(getEl(), manuallyDisabledButtons);
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
