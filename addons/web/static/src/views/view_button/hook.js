/* @odoo-module */

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
        async onClickViewButton({ clickParams, record }) {
            const manuallyDisabledButtons = disableButtons(getEl());

            const _continue = await beforeExecuteAction(clickParams);
            if (typeof _continue !== "undefined" && !_continue) {
                enableButtons(getEl(), manuallyDisabledButtons);
                return;
            }

            const resId = record.resId;
            const resIds = record.resIds || model.resIds;
            const resModel = record.resModel || model.resModel;

            const valuesForEval = Object.assign({}, record.data, {
                active_id: resId,
                active_ids: resIds,
            });

            let buttonContext = {};
            if (clickParams.context) {
                buttonContext = evaluateExpr(clickParams.context, valuesForEval);
            }
            if (clickParams.buttonContext) {
                Object.assign(buttonContext, clickParams.buttonContext);
            }
            const envContext = record.context || {}; //LPE FIXME new Context(payload.env.context).eval();

            const doActionParams = Object.assign({}, clickParams, {
                resModel,
                resId,
                resIds,
                context: envContext,
                buttonContext,
                onClose: async () => {
                    const reload = options.reload || (() => record.model.root.load());
                    await reload();
                    comp.render(true); // FIXME WOWL reactivity
                },
            });

            try {
                if (clickParams.confirm) {
                    await new Promise((resolve) => {
                        const dialogProps = {
                            body: clickParams.confirm,
                            confirm: async () => await action.doActionButton(doActionParams),
                            cancel: () => {},
                        };
                        dialog.add(ConfirmationDialog, dialogProps, { onClose: resolve });
                    });
                } else {
                    await action.doActionButton(doActionParams);
                }
            } finally {
                enableButtons(getEl(), manuallyDisabledButtons);
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
