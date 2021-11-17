/* @odoo-module */

import { useListener } from "web.custom_hooks";
import { useService } from "@web/core/utils/hooks";
import { evaluateExpr } from "@web/core/py_js/py";

function toggleButtonsDisable(el, enable = true) {
    const btns = el.querySelectorAll("button");
    let apply;
    if (enable) {
        apply = (btn) => btn.removeAttribute("disabled");
    } else {
        apply = (btn) => btn.setAttribute("disabled", "1");
    }
    for (const btn of btns) {
        apply(btn);
    }
}

export function useViewButtons(model) {
    const action = useService("action");
    const comp = owl.hooks.useComponent();

    async function handler(ev) {
        toggleButtonsDisable(comp.el, false);
        const { clickParams, record } = ev.detail;
        const { resIds } = model;

        const resId = record.resId;
        const resModel = record.resModel || model.resModel;

        const valuesForEval = Object.assign({}, record.data, {
            active_id: resId,
            active_ids: resIds,
        });

        let buttonContext;
        if (clickParams.context) {
            buttonContext = evaluateExpr(clickParams.context, valuesForEval);
        }
        const envContext = record.context; //LPE FIXME new Context(payload.env.context).eval();

        const doActionParams = Object.assign({}, clickParams, {
            resModel,
            resId,
            resIds,
            context: envContext,
            buttonContext,
            onClose: () => model.load(),
        });

        try {
            await action.doActionButton(doActionParams);
        } finally {
            if (comp.el) {
                toggleButtonsDisable(comp.el, true);
            }
        }
    }

    useListener("action-button-clicked", handler);
}
