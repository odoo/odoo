/* @odoo-module */

import { DiscussPublic } from "@mail/discuss/core/public/discuss_public";
import { data } from "mail.discuss_public_template";

import { Component, mount, whenReady } from "@odoo/owl";

import { templates } from "@web/core/assets";
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { makeEnv, startServices } from "@web/env";
import { mapLegacyEnvToWowlEnv } from "@web/legacy/utils";
import * as legacyEnv from "web.env";

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
