import { DiscussClientAction } from "@mail/core/public_web/discuss_app/client_action";

import { whenReady } from "@odoo/owl";

import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { mountComponent } from "@web/env";
import { session } from "@web/session";

(async function boot() {
    // Like `startWebClient`, which this page doesn't use.
    odoo.info = {
        db: session.db,
        server_version: session.server_version,
        server_version_info: session.server_version_info,
        isEnterprise: session.server_version_info.slice(-1)[0] === "e",
    };
    await whenReady();

    const mainComponentsRegistry = registry.category("main_components");
    mainComponentsRegistry.add("DiscussClientAction", { Component: DiscussClientAction });

    await mountComponent(MainComponentsContainer, document.body, { name: "Discuss" });
    odoo.isReady = true;
})();
