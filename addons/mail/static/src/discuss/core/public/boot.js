import { DiscussClientAction } from "@mail/core/public_web/discuss_app/client_action";

import { App, whenReady } from "@odoo/owl";

import { getTemplate } from "@web/core/templates";
import { appTranslateFn } from "@web/core/l10n/translation";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { makeEnv, startServices } from "@web/env";

(async function boot() {
    await whenReady();

    const mainComponentsRegistry = registry.category("main_components");
    mainComponentsRegistry.add("DiscussClientAction", { Component: DiscussClientAction });

    const env = makeEnv();
    const app = new App({
        env,
        getTemplate,
        dev: env.debug,
        translatableAttributes: ["data-tooltip"],
        translateFn: appTranslateFn,
        plugins: services,
    });
    await startServices(env, app);
    env.services["mail.store"].insert(odoo.discuss_data);
    odoo.isReady = true;
    const root = await app.createRoot(MainComponentsContainer).mount(document.body);
    odoo.__WOWL_DEBUG__ = { root };
})();
