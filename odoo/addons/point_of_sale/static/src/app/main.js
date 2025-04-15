/** @odoo-module */

import { Chrome } from "@point_of_sale/app/pos_app";
import { Loader } from "@point_of_sale/app/loader/loader";
import { templates } from "@web/core/assets";
import { App, mount, reactive, whenReady } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { hasTouch } from "@web/core/browser/feature_detection";
import { localization } from "@web/core/l10n/localization";
import { makeEnv, startServices } from "@web/env";
import { session } from "@web/session";
import { RPCError } from "@web/core/network/rpc_service";

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

    // setup environment
    const env = makeEnv();
    await startServices(env);

    // handle loading PoS error
    if (env.services.pos instanceof Error) {
        let message = _t("An error occurred while loading the Point of Sale: \n");
        if (env.services.pos instanceof RPCError) {
            message += env.services.pos.data.message;
        } else {
            message += env.services.pos.message;
        }
        window.alert(message);
        window.location = "/web#action=point_of_sale.action_client_pos_menu";
    }

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
