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
        this.portalSecurity = {};
    }

    async createShadow(root) {
        const shadow = root.attachShadow({ mode: "open" });
        const res = await getBundle("portal.assets_embed");
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
            portalSecurity: {
                token: chatterEl.getAttribute("data-token"),
                hash: chatterEl.getAttribute("data-hash"),
                pid: parseInt(chatterEl.getAttribute("data-pid")),
            },
            composer:
                parseInt(chatterEl.getAttribute("data-allow_composer")) &&
                (chatterEl.getAttribute("data-token") || session.user_id),
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
        this.portalSecurity = props.portalSecurity;
        await rpc(
            "/portal/chatter_init",
            {
                thread_model: props.resModel,
                thread_id: props.resId,
                token: props.portalSecurity.token,
            },
            { silent: true }
        ).then((data) => {
            env.services["mail.store"].self = data;
            const channelParams = {
                thread_model: props.resModel,
                thread_id: props.resId,
            };
            if (props.portalSecurity.token) {
                channelParams.token = props.portalSecurity.token;
            }
            if (props.portalSecurity.hash && props.portalSecurity.pid) {
                channelParams.hash = props.portalSecurity.hash;
                channelParams.pid = props.portalSecurity.pid;
            }
            env.services["bus_service"].addChannel(
                `portal.channel_${JSON.stringify(channelParams)}`
            );
        });
    }
}

export const portalChatterService = {
    start(env, services) {
        const portalChatter = new PortalChatterService(env, services);
        portalChatter.initialize(env);
        return portalChatter;
    },
};
registry.category("services").add("portal.chatter", portalChatterService);
