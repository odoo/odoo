import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";

const loader = {
    loadChatter: memoize(() => loadBundle("portal.assets_chatter")),
};
export class PortalChatterBootService {
    async initialize(env) {
        const chatterEl = document.querySelector(".o_portal_chatter");
        if (chatterEl) {
            loader.loadChatter();
        }
    }
}

export const portalChatterBootService = {

    start(env, services) {
        const PortalChatterBoot = new PortalChatterBootService(env, services);
        PortalChatterBoot.initialize(env);
        return PortalChatterBoot;
    },
};
registry.category("services").add("portal.chatter.boot", portalChatterBootService);
