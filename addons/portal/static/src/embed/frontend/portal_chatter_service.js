/* @odoo-module */

import { ChatterRoot } from "@portal/embed/frontend/chatter_root";
import { App } from "@odoo/owl";
import { templates, getBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { session } from "@web/session";

export class PortalChatterService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.env = env;
        /** @type {string} */
        this.token = null;
        this.store = services["mail.store"];
        this.rpc = services.rpc;
        this.busService = services.bus_service;
    }

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
    }

    async initialize(env) {
        const chatterEl = document.querySelector(".o_portal_chatter");
        if (chatterEl) {
            const props = {
                resId: chatterEl.getAttribute("data-res_id"),
                resModel: chatterEl.getAttribute("data-res_model"),
                dataToken: chatterEl.getAttribute("data-token"),
                hasComposer:
                    parseInt(chatterEl.getAttribute("data-allow_composer")) &&
                    (chatterEl.getAttribute("data-token") || session.user_id),
                twoColumns: chatterEl.getAttribute("data-two_columns") === "true" ? true : false,
                displayRating:
                    chatterEl.getAttribute("data-display_rating") === "True" ? true : false,
            };
            this.busService.addChannel(`portal_Chatter-${props.dataToken}`);
            const root = document.createElement("div");
            root.setAttribute("id", "chatterRoot");
            root.classList.add("o-chatter-root");
            if (props.twoColumns) {
                root.classList.add("p-0", "bg-white");
            }
            chatterEl.appendChild(root);
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
            this.token = props.dataToken;
            await this.rpc(
                "/mail/chatter_init",
                { res_model: props.resModel, res_id: props.resId },
                { silent: true }
            ).then((data) => {
                this.store.user = this.store.Persona.insert({
                    ...data,
                    type: "partner",
                });
            });
        }
    }
}

export const portalChatterService = {
    dependencies: ["mail.store", "rpc", "bus_service"],

    start(env, services) {
        const portalChatter = new PortalChatterService(env, services);
        portalChatter.initialize(env);
        return portalChatter;
    },
};
registry.category("services").add("portal.chatter", portalChatterService);
