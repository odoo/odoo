/** @odoo-module */

import { Chrome } from "@point_of_sale/app/pos_app";
import { Loader } from "@point_of_sale/app/loader/loader";
import { setLoadXmlDefaultApp, templates } from "@web/core/assets";
import { App, mount, reactive, whenReady, Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { hasTouch } from "@web/core/browser/feature_detection";
import { localization } from "@web/core/l10n/localization";
import { renderToString } from "@web/core/utils/render";
import { makeEnv, startServices } from "@web/env";
import { session } from "@web/session";

const loader = reactive({ isShown: true });
whenReady(() => {
    // Show loader as soon as the page is ready, do not wait for services to be started
    // as some services load data over RPC and this is why we want to show a loader.
    mount(Loader, document.body, { templates, translateFn: _t, props: { loader } });
});
// The following is mostly a copy of startWebclient but without any of the legacy stuff
(async function startPosApp() {
    odoo.info = {
        db: session.db,
        server_version: session.server_version,
        server_version_info: session.server_version_info,
        isEnterprise: session.server_version_info.slice(-1)[0] === "e",
    };

    // Wait for all templates
    await odoo.ready(/\.bundle\.xml/);
    // Make a temporary app to be able to use renderToString method before the main app is available.
    const renderToStringApp = new App(Component, {
        name: "renderToString app",
        templates,
        dev: !!odoo.debug,
        warnIfNoStaticProps: true,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
    });
    renderToString.app = renderToStringApp;

    // setup environment
    const env = makeEnv();
    await startServices(env);
    // start application
    await whenReady();
    const app = new App(Chrome, {
        name: "Odoo Point of Sale",
        env,
        templates,
        dev: env.debug,
        warnIfNoStaticProps: true,
        translatableAttributes: ["data-tooltip"],
        translateFn: _t,
        props: { disableLoader: () => (loader.isShown = false) },
    });
    renderToString.app = app;
    setLoadXmlDefaultApp(app);
    const root = await app.mount(document.body);
    const classList = document.body.classList;
    if (localization.direction === "rtl") {
        classList.add("o_rtl");
    }
    if (env.services.user.userId === 1) {
        classList.add("o_is_superuser");
    }
    if (env.debug) {
        classList.add("o_debug");
    }
    if (hasTouch()) {
        classList.add("o_touch_device");
    }
    // delete odoo.debug; // FIXME: some legacy code rely on this
    odoo.__WOWL_DEBUG__ = { root };
})();
