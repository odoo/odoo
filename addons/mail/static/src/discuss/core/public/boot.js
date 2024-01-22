/* @odoo-module */

import { DiscussPublic } from "@mail/discuss/core/public/discuss_public";

import { mount, whenReady } from "@odoo/owl";

import { getTemplate } from "@web/core/templates";
import { OverlayContainer } from "@web/core/overlay/overlay_container";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";

(async function boot() {
    await whenReady();

    const overlaysRegistry = registry.category("overlays");
    overlaysRegistry.add("DiscussPublic", {
        component: DiscussPublic,
        props: { data: odoo.discuss_data },
    });

    const env = makeEnv();
    await startServices(env);
    env.services["mail.store"].inPublicPage = true;
    odoo.isReady = true;
    await mount(OverlayContainer, document.body, { env, getTemplate, dev: env.debug });
})();
