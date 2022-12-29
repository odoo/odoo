/** @odoo-module **/

import { data } from "mail.discuss_public_template";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
// import { session } from "@web/session";
import { templates } from "@web/core/assets";

// import * as legacySession from "web.session";

import { mount, whenReady } from "@odoo/owl";
import { DiscussPublic } from "./discuss_public";

(async function boot() {
    await whenReady();

    const mainComponentsRegistry = registry.category("main_components");
    mainComponentsRegistry.add("DiscussPublic", {
        Component: DiscussPublic,
        props: { data },
    });

    // await legacySession.is_bound;
    // Object.assign(odoo, {
    //     info: {
    //         db: session.db,
    //         server_version: session.server_version,
    //         server_version_info: session.server_version_info,
    //         isEnterprise: session.server_version_info.slice(-1)[0] === "e",
    //     },
    //     isReady: false,
    // });
    const env = makeEnv();
    await startServices(env);
    odoo.isReady = true;
    await mount(MainComponentsContainer, document.body, { env, templates, dev: env.debug });
})();
