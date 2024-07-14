/** @odoo-module **/
import { PreparationDisplay } from "@pos_preparation_display/app/components/preparation_display/preparation_display";
import { makeEnv, startServices } from "@web/env";
import { App, whenReady } from "@odoo/owl";
import { templates } from "@web/core/assets";
import { session } from "@web/session";
import { _t } from "@web/core/l10n/translation";

(async function setup() {
    odoo.info = {
        db: session.db,
        server_version: session.server_version,
        server_version_info: session.server_version_info,
        isEnterprise: session.server_version_info.slice(-1)[0] === "e",
    };
    odoo.isReady = false;

    const env = makeEnv();
    await startServices(env);
    await whenReady();

    const app = new App(PreparationDisplay, {
        env,
        templates,
        dev: env.debug,
        warnIfNoStaticProps: true,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
    });
    const root = await app.mount(document.body);

    odoo.__WOWL_DEBUG__ = { root };
    odoo.isReady = true;
})();
