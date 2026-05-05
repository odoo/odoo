import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { Interaction } from "@web/public/interaction";
import { session } from "@web/session";

odoo.portalChatterReady = Promise.withResolvers();

const loadChatter = memoize(() => loadBundle("portal.assets_chatter"));

export class PortalChatterBoot extends Interaction {
    static selector = ".o_portal_chatter";

    setup() {
        this.root = document.createElement("div");
        this.root.setAttribute("id", "chatterRoot");
        this.el.appendChild(this.root);
        if (this.el.dataset.two_columns === "true") {
            this.root.classList.add("p-0");
        }
    }

    async willStart() {
        await loadChatter();
        this.shadowRoot = this.root.attachShadow({ mode: "open" });
        const { loadCssFromBundle } = odoo.loader.modules.get("@mail/utils/common/misc");
        await loadCssFromBundle(this.shadowRoot, "portal.assets_chatter_style");
    }

    start() {
        const { PortalChatter } = odoo.loader.modules.get("@portal/chatter/portal/portal_chatter");
        const dataset = this.el.dataset;
        const props = {
            composer: !!(parseInt(dataset.allow_composer) && (dataset.token || !session.is_public)),
            displayRating: dataset.display_rating === "True",
            resId: parseInt(dataset.res_id),
            resModel: dataset.res_model,
            twoColumns: dataset.two_columns === "true",
        };
        this.mountComponent(this.shadowRoot, PortalChatter, props);
        const thread = this.env.services["mail.store"]["mail.thread"].insert({
            access_token: dataset.token,
            hash: dataset.hash,
            id: dataset.res_id,
            model: dataset.res_model,
            pid: parseInt(dataset.pid),
        });
        this.env.services["mail.store"]
            .fetchStoreData(
                "/portal/chatter_init",
                {
                    access_params: thread.rpcParams,
                    thread_id: props.resId,
                    thread_model: props.resModel,
                },
                { readonly: false }
            )
            .then(() => {
                odoo.portalChatterReady.resolve(true);
            });
    }
}

registry.category("public.interactions").add("portal.chatter.boot", PortalChatterBoot);
