import { PortalChatter } from "@portal/chatter/frontend/portal_chatter";
import { App } from "@odoo/owl";
import { getBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";
import { getTemplate } from "@web/core/templates";

export class PortalChatterService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.store = services["mail.store"];
        this.busService = services.bus_service;
    }

    async createShadow(root) {
        const shadow = root.attachShadow({ mode: "open" });
        const res = await getBundle("portal.assets_chatter_style");
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
        const props = {
            resId: parseInt(chatterEl.getAttribute("data-res_id")),
            resModel: chatterEl.getAttribute("data-res_model"),
            composer:
                parseInt(chatterEl.getAttribute("data-allow_composer")) &&
                (chatterEl.getAttribute("data-token") || !session.is_public),
            twoColumns: chatterEl.getAttribute("data-two_columns") === "true" ? true : false,
            displayRating: chatterEl.getAttribute("data-display_rating") === "True" ? true : false,
        };
        const root = document.createElement("div");
        root.setAttribute("id", "chatterRoot");
        if (props.twoColumns) {
            root.classList.add("p-0");
        }
        chatterEl.appendChild(root);
        this.createShadow(root).then((shadow) => {
            new App(PortalChatter, {
                env,
                getTemplate,
                props,
                translatableAttributes: ["data-tooltip"],
                translateFn: _t,
                dev: env.debug,
            }).mount(shadow);
        });
        const thread = this.store.Thread.insert({ model: props.resModel, id: props.resId });
        Object.assign(thread, {
            access_token: chatterEl.getAttribute("data-token"),
            hash: chatterEl.getAttribute("data-hash"),
            pid: parseInt(chatterEl.getAttribute("data-pid")),
        });
        const data = await rpc(
            "/portal/chatter_init",
            {
                thread_model: props.resModel,
                thread_id: props.resId,
                ...thread.rpcParams,
            },
            { silent: true }
        );
        this.store.insert(data);
        odoo.portalChatterReady.resolve(true);
    }
}

export const portalChatterService = {
    dependencies: ["mail.store", "bus_service"],
    start(env, services) {
        const portalChatter = new PortalChatterService(env, services);
        portalChatter.initialize(env);
        return portalChatter;
    },
};
registry.category("services").add("portal.chatter", portalChatterService);
