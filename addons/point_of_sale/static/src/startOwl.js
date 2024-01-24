/** @odoo-module */

import { getTemplate } from "@web/core/templates";
import { App, whenReady } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { makeEnv, startServices } from "@web/env";

export async function startOwl(root, settings = {}) {
    const env = makeEnv();
    await startServices(env);
    await whenReady();
    const app = new App(root, {
        env,
        getTemplate,
        dev: env.debug,
        warnIfNoStaticProps: true,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
        ...settings,
    });
    await app.mount(document.body);
    return app;
}
