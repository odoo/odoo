/* @odoo-module */

import { ChatterRoot } from "@portal/embed/frontend/chatter_root";
import { App } from "@odoo/owl";
import { templates, getBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";

export class PortalChatterService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        /** @type {string} */
        this.token = null;
    }
}

export const portalChatterService = {
    dependencies: ["bus_service", "mail.messaging"],

    async createShadow(root) {
        const shadow = root.attachShadow({ mode: "open" });
        const res = await getBundle("portal.assets_chatter");
        for (const url of res.cssLibs) {
            const link = document.createElement("link");
            link.rel = "stylesheet";
            link.href = url;
            shadow.appendChild(link);
            await new Promise((res, rej) => {
                link.addEventListener("load", res);
                link.addEventListener("error", rej);
            });
        }
        return shadow;
    },

    start(env, services) {
        const portalChatter = new PortalChatterService(env, services);
        const chatterEl = document.querySelector(".o_portal_chatter");
        services.bus_service.addChannel(`portal_Chatter-${chatterEl.getAttribute("data-token")}`);
        if (chatterEl) {
            const root = document.createElement("div");
            root.setAttribute("id", "chatterRoot");
            root.classList.add("o-chatter-root");
            chatterEl.appendChild(root);
            const props = {
                resId: chatterEl.getAttribute("data-res_id"),
                resModel: chatterEl.getAttribute("data-res_model"),
                dataToken: chatterEl.getAttribute("data-token"),
            };
            this.createShadow(root).then((shadow) => {
                new App(ChatterRoot, {
                    env,
                    templates,
                    props,
                    translatableAttributes: ["data-tooltip"],
                    translateFn: env._t,
                    dev: env.debug,
                }).mount(shadow);
            });
            portalChatter.token = chatterEl.getAttribute("data-token");
        }
        return portalChatter;
    },
};
registry.category("services").add("portal.chatter", portalChatterService);
