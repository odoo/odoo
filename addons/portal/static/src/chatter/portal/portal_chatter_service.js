import { loadCssFromBundle } from "@mail/utils/common/misc";
import { PortalChatter } from "@portal/chatter/portal/portal_chatter";
import { registry } from "@web/core/registry";
import { useRootCreator } from "@web/core/utils/hooks";
import { session } from "@web/session";

export class PortalChatterService {
    constructor(env, services) {
        this.setup(env, services);
    }

    createRoot = useRootCreator();

    setup(env, services) {
        this.store = services["mail.store"];
        this.busService = services.bus_service;
    }

    async createShadow(rootEl) {
        const shadow = rootEl.attachShadow({ mode: "open" });
        await loadCssFromBundle(shadow, "portal.assets_chatter_style");
        return shadow;
    }

    /** @param {HTMLElement} chatterEl */
    getProps(chatterEl) {
        return {
            resId: parseInt(chatterEl.getAttribute("data-res_id")),
            resModel: chatterEl.getAttribute("data-res_model"),
            composer: Boolean(
                parseInt(chatterEl.getAttribute("data-allow_composer")) &&
                    (chatterEl.getAttribute("data-token") || !session.is_public)
            ),
            twoColumns: chatterEl.getAttribute("data-two_columns") === "true" ? true : false,
            displayRating: chatterEl.getAttribute("data-display_rating") === "True" ? true : false,
        };
    }

    /** @param {import("@web/env").OdooEnv} env */
    async initialize(env) {
        const chatterEl = document.querySelector(".o_portal_chatter");
        const props = this.getProps(chatterEl);
        const rootEl = chatterEl.querySelector("#chatterRoot");
        if (props.twoColumns) {
            rootEl.classList.add("p-0");
        }
        this.createShadow(rootEl).then((shadow) => {
            const root = this.createRoot(PortalChatter, {
                env: Object.assign(Object.create(env), {
                    rootId: rootEl.getAttribute("id"),
                }),
                props,
            });
            return root.mount(shadow);
        });
        const thread = this.store["mail.thread"].insert({ model: props.resModel, id: props.resId });
        Object.assign(thread, {
            access_token: chatterEl.getAttribute("data-token"),
            hash: chatterEl.getAttribute("data-hash"),
            pid: parseInt(chatterEl.getAttribute("data-pid")),
        });
        await this.store.fetchStoreData("/portal/chatter_init", {
            access_params: thread.rpcParams,
            thread_id: props.resId,
            thread_model: props.resModel,
        });
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
