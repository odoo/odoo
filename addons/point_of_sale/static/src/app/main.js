import { Loader } from "@point_of_sale/app/components/loader/loader";
import { getTemplate } from "@web/core/templates";
import { mount, reactive, whenReady } from "@odoo/owl";
import { _t, appTranslateFn } from "@web/core/l10n/translation";
import { hasTouch } from "@web/core/browser/feature_detection";
import { localization } from "@web/core/l10n/localization";
import { user } from "@web/core/user";
import { session } from "@web/session";
import { mountComponent } from "@web/env";
import { Chrome } from "@point_of_sale/app/pos_app";

const loader = reactive({ isShown: true, error: false });
whenReady(() => {
    mount(Loader, document.body, {
        getTemplate,
        props: { loader },
        translatableAttributes: ["data-tooltip"],
        translateFn: appTranslateFn,
    });
});

(async function startPosApp() {
    odoo.info = {
        db: session.db,
        server_version: session.server_version,
        server_version_info: session.server_version_info,
        isEnterprise: session.server_version_info.slice(-1)[0] === "e",
    };
    await whenReady();
    try {
        const app = await mountComponent(Chrome, document.body, {
            name: "Odoo Point of Sale",
            props: { disableLoader: () => (loader.isShown = false) },
        });
        window.addEventListener("beforeunload", function (event) {
            if (app.env.services.pos_data.network.offline) {
                var confirmationMessage = _t(
                    "You are currently offline. Reloading the page may cause you to lose unsaved data."
                );
                event.returnValue = confirmationMessage;
                return confirmationMessage;
            }
        });
        const classList = document.body.classList;
        if (localization.direction === "rtl") {
            classList.add("o_rtl");
        }
        if (user.userId === 1) {
            classList.add("o_is_superuser");
        }
        if (app.env.debug) {
            classList.add("o_debug");
        }
        if (hasTouch()) {
            classList.add("o_touch_device");
            classList.add("o_mobile_overscroll");
            document.documentElement.classList.add("o_mobile_overscroll");
        }

        registerServiceWorker();
    } catch (e) {
        loader.error = e;
        throw e;
    }
})();

function registerServiceWorker() {
    // Register the service worker for the POS
    const urlsToCache = JSON.parse(odoo.urls_to_cache);
    urlsToCache.push("/web/static/lib/zxing-library/zxing-library.js");

    navigator.serviceWorker?.register("/pos/service-worker.js").then((registration) => {
        const worker = registration.installing || registration.waiting || registration.active;
        worker.postMessage({ urlsToCache });
    });
}
