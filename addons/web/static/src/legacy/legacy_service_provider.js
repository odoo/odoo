/** @odoo-module **/

import { bus } from "web.core";
import Context from "web.Context";

import { browser } from "../core/browser/browser";
import { registry } from "../core/registry";
import { mapDoActionOptionAPI } from "./backend_utils";
import { wrapSuccessOrFail } from "@web/legacy/utils";

export const legacyServiceProvider = {
    dependencies: ["effect", "action"],
    start({ services }) {
        browser.addEventListener("show-effect", (ev) => {
            services.effect.add(ev.detail);
        });
        bus.on("show-effect", this, (payload) => {
            services.effect.add(payload);
        });

        browser.addEventListener("do-action", (ev) => {
            const payload = ev.detail;
            if (payload.action.context) {
                payload.action.context = new Context(payload.action.context).eval();
            }
            const legacyOptions = mapDoActionOptionAPI(payload.options);
            services.action.doAction(payload.action, legacyOptions);
        });

        browser.addEventListener("execute-action", (ev) => {
            const payload = ev.detail;
            const buttonContext = new Context(payload.action_data.context).eval();
            const envContext = new Context(payload.env.context).eval();
            wrapSuccessOrFail(
                services.action.doActionButton({
                    args: payload.action_data.args,
                    buttonContext: buttonContext,
                    context: envContext,
                    close: payload.action_data.close,
                    resModel: payload.env.model,
                    name: payload.action_data.name,
                    resId: payload.env.currentID || null,
                    resIds: payload.env.resIDs,
                    special: payload.action_data.special,
                    type: payload.action_data.type,
                    onClose: payload.on_closed,
                    effect: payload.action_data.effect,
                }),
                payload
            );
        });
    },
};

registry.category("services").add("legacy_service_provider", legacyServiceProvider);
