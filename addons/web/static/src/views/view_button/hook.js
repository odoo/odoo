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

export function useViewButtons(model, ref, beforeExecuteAction = () => {}) {
    const action = useService("action");
    const dialog = useService("dialog");
    const comp = owl.useComponent();
    const env = useEnv();
    useSubEnv({
        async onClickViewButton({ clickParams, record }) {
            const manuallyDisabledButtons = disableButtons(getEl());

            await beforeExecuteAction(clickParams);

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
                    await record.load();
                    comp.render(true); // FIXME WOWL reactivity
                },
            });

            try {
                if (clickParams.confirm) {
                    const dialogProps = {
                        body: clickParams.confirm,
                        confirm: async () => await action.doActionButton(doActionParams),
                        cancel: () => {},
                    };
                    dialog.add(ConfirmationDialog, dialogProps);
                } else {
                    await action.doActionButton(doActionParams);
                }
            } finally {
                if (getEl()) {
                    for (const btn of manuallyDisabledButtons) {
                        btn.removeAttribute("disabled");
                    }
                }
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
