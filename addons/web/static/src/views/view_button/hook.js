/* @odoo-module */

import { useListener, useService } from "@web/core/utils/hooks";
import { evaluateExpr } from "@web/core/py_js/py";

function disableButtons(el) {
    const btns = el.querySelectorAll("button");
    const manuallyDisabledButtons = [];
    for (const btn of btns) {
        if (!btn.hasAttribute("disabled")) {
            manuallyDisabledButtons.push(btn);
            btn.setAttribute("disabled", "1");
        }
    }
    return manuallyDisabledButtons;
}

export function useViewButtons(model, beforeExecuteAction = () => {}) {
    const action = useService("action");
    const comp = owl.useComponent();

    async function handler(ev) {
        const manuallyDisabledButtons = disableButtons(comp.el);
        const { clickParams, record } = ev.detail;

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
                await model.root.load();
                comp.render();
            },
        });

        try {
            await action.doActionButton(doActionParams);
        } finally {
            if (comp.el) {
                for (const btn of manuallyDisabledButtons) {
                    btn.removeAttribute("disabled");
                }
            }
        }
    }

    useListener("action-button-clicked", handler);
}
