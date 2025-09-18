import { DiscussClientAction } from "@mail/core/public_web/discuss_client_action";
import { mount, whenReady } from "@odoo/owl";
import { MainComponentsContainer } from "@web/components/main_components_container";
import { appTranslateFn } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { getTemplate } from "@web/core/templates";
import { makeEnv, startServices } from "@web/env";

(async function boot() {
    await whenReady();

    const mainComponentsRegistry = registry.category("main_components");
    mainComponentsRegistry.add("DiscussClientAction", {
        Component: DiscussClientAction,
    });

    const env = makeEnv();
    await startServices(env);
    env.services["mail.store"].insert(odoo.discuss_data);
    odoo.isReady = true;
    const root = await mount(MainComponentsContainer, document.body, {
        env,
        getTemplate,
        dev: env.debug,
        translatableAttributes: ["data-tooltip"],
        translateFn: appTranslateFn,
    });
    odoo.__WOWL_DEBUG__ = { root };
})();
