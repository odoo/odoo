/* @odoo-module */

import { useListener } from "web.custom_hooks";
import { useService } from "@web/core/service_hook";
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

export function useActionButtons(model) {
    const action = useService("action");
    const comp = owl.hooks.useComponent();

    async function handler(ev) {
        toggleButtonsDisable(comp.el, false);
        const { clickParams, record } = ev.detail;
        const { resModel, resIds } = model;

        const resId = record.resId;

        const valuesForEval = Object.assign({}, record.data, {
            active_id: resId,
            active_ids: resIds,
        });

        let buttonContext;
        if (clickParams.context) {
            buttonContext = evaluateExpr(clickParams.context, valuesForEval);
        }
        const envContext = null; //LPE FIXME record.context ?? new Context(payload.env.context).eval();

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
