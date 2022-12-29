/** @odoo-module **/

import { data } from "mail.discuss_public_template";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import { templates } from "@web/core/assets";

import { mapLegacyEnvToWowlEnv } from "@web/legacy/utils";

import * as legacyEnv from "web.env";
import { Component, mount, whenReady } from "@odoo/owl";
import { DiscussPublic } from "@mail/new/public/discuss_public";

Component.env = legacyEnv;

(async function boot() {
    await whenReady();

    const mainComponentsRegistry = registry.category("main_components");
    mainComponentsRegistry.add("DiscussPublic", {
        Component: DiscussPublic,
        props: { data },
    });

    const env = makeEnv();
    await startServices(env);
    env.services["mail.store"].inPublicPage = true;
    mapLegacyEnvToWowlEnv(Component.env, env);
    odoo.isReady = true;
    await mount(MainComponentsContainer, document.body, { env, templates, dev: env.debug });
})();
