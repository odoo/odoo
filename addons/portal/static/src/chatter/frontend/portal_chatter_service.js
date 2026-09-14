/** @odoo-module native */
import { loadCssFromBundle } from "@mail/utils/common/misc";
import { App } from "@odoo/owl";
import { PortalChatter } from "@portal/chatter/frontend/portal_chatter";
import { makeLogger } from "@web/core/debug/debug_logger";
import { ConnectionLostError, rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { getTemplate } from "@web/core/templates";
import { appTranslateFn } from "@web/core/translation";
import { attachShadowRoot } from "@web/core/utils/dom/ui";
import { session } from "@web/session";

const log = makeLogger("portal.chatter");

export class PortalChatterService {
    constructor(env, services) {
        this.setup(env, services);
    }

    setup(env, services) {
        this.store = services["mail.store"];
    }

    async createShadow(root) {
        const shadow = attachShadowRoot(root);
        await loadCssFromBundle(shadow, "portal.assets_chatter_style");
        return shadow;
    }

    async initialize(env) {
        const chatterEl = document.querySelector(".o_portal_chatter");
        if (!chatterEl) {
            odoo.portalChatterReady.resolve(false);
            return;
        }
        const props = {
            resId: parseInt(chatterEl.getAttribute("data-res_id"), 10),
            resModel: chatterEl.getAttribute("data-res_model"),
            composer:
                parseInt(chatterEl.getAttribute("data-allow_composer"), 10) &&
                (chatterEl.getAttribute("data-token") || !session.is_public),
            twoColumns: chatterEl.getAttribute("data-two_columns") === "true",
            displayRating: chatterEl.getAttribute("data-display_rating") === "True",
        };
        const root = document.createElement("div");
        root.setAttribute("id", "chatterRoot");
        if (props.twoColumns) {
            root.classList.add("p-0");
        }
        chatterEl.appendChild(root);
        let app;
        try {
            const thread = this.store.Thread.insert({
                model: props.resModel,
                id: props.resId,
            });
            Object.assign(thread, {
                access_token: chatterEl.getAttribute("data-token"),
                hash: chatterEl.getAttribute("data-hash"),
                pid: parseInt(chatterEl.getAttribute("data-pid"), 10),
            });
            const [shadow, data] = await Promise.all([
                this.createShadow(root),
                rpc(
                    "/portal/chatter_init",
                    {
                        thread_model: props.resModel,
                        thread_id: props.resId,
                        ...thread.rpcParams,
                    },
                    { silent: true },
                ),
            ]);
            this.store.insert(data);
            app = new App(PortalChatter, {
                env,
                getTemplate,
                props,
                translatableAttributes: ["data-tooltip"],
                translateFn: appTranslateFn,
                dev: env.debug,
            });
            await app.mount(shadow);
            log.lifecycle("mounted");
            odoo.portalChatterReady.resolve(true);
        } catch (error) {
            app?.destroy();
            root.remove();
            log.lifecycle("initialization failed");
            throw error;
        }
    }
}

export const portalChatterService = {
    dependencies: ["mail.store", "bus_service"],
    start(env, services) {
        const portalChatter = new PortalChatterService(env, services);
        portalChatter.initialize(env).catch((error) => {
            odoo.portalChatterReady.resolve(false);
            if (error instanceof ConnectionLostError) {
                // the connection handlers own a lost or cut transport; a
                // request interrupted by navigating away is the usual one
                throw error;
            }
            console.error("Portal chatter failed to initialize", error);
        });
        return portalChatter;
    },
};
registry.category("services").add("portal.chatter", portalChatterService);
