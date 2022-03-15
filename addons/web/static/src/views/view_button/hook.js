/* @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { evaluateExpr } from "@web/core/py_js/py";

const { useRef, useSubEnv } = owl;

function disableButtons(el) {
    // WOWL: can we do this non-imperatively?
    const btns = [...el.querySelectorAll("button:not([disabled])")];
    for (const btn of btns) {
        btn.setAttribute("disabled", "1");
    }
    return btns;
}

export function useViewButtons(model, beforeExecuteAction = () => {}, refName = "root") {
    const action = useService("action");
    const comp = owl.useComponent();
    const ref = useRef(refName);
    useSubEnv({
        async onClickViewButton({ clickParams, record }) {
            const manuallyDisabledButtons = disableButtons(ref.el);

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
                    comp.render(true); // FIXME WOWL reactivity
                },
            });

            try {
                await action.doActionButton(doActionParams);
            } finally {
                if (ref.el) {
                    for (const btn of manuallyDisabledButtons) {
                        btn.removeAttribute("disabled");
                    }
                }
            }
        },
    });
}
