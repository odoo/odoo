/** @odoo-module **/

import core from "web.core";
import session from "web.session";
import { _t } from "web.core";
import { browser, makeRAMLocalStorage } from "@web/core/browser/browser";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { legacyProm } from "web.test_legacy";
import { registerCleanup } from "./helpers/cleanup";
import { prepareRegistriesWithCleanup } from "./helpers/mock_env";
import { session as sessionInfo } from "@web/session";
import { prepareLegacyRegistriesWithCleanup } from "./helpers/legacy_env_utils";
import { config as transitionConfig } from "@web/core/transition";

transitionConfig.disabled = true;

import { patch } from "@web/core/utils/patch";
import { processTemplates } from "@web/core/assets";
const { App, whenReady, loadFile } = owl;

patch(App.prototype, "TestOwlApp", {
    destroy() {
        if (!this.destroyed) {
            this._super(...arguments);
            this.destroyed = true;
        }
    },
    addTemplate(name) {
        registerCleanup(() => {
            delete this.constructor.sharedTemplates[name];
        });
        return this._super(...arguments);
    },
});

function stringifyObjectValues(obj, properties) {
    let res = "";
    for (const dotted of properties) {
        const keys = dotted.split(".");
        let val = obj;
        for (const k of keys) {
            val = val[k];
        }
        res += JSON.stringify(val);
    }
    return res;
}

function checkGlobalObjectsIntegrity() {
    const objects = [
        [session, ["user_context", "currencies"]],
        [_t, ["database.multi_lang", "database.parameters"]],
    ];
    const initials = objects.map((obj) => stringifyObjectValues(obj[0], obj[1]));

    registerCleanup((infos) => {
        const finals = objects.map((obj) => stringifyObjectValues(obj[0], obj[1]));
        for (const index in initials) {
            if (initials[index] !== finals[index]) {
                const [global, keys] = objects[index];
                throw new Error(
                    `The keys "${keys}" of some global objects (usually session or _t) may have been polluted by the test "${infos.testName}" in module "${infos.moduleName}"`
                );
            }
        }
    });
}

function forceLocaleAndTimezoneWithCleanup() {
    const originalLocale = luxon.Settings.defaultLocale;
    luxon.Settings.defaultLocale = "en";
    const originalZone = luxon.Settings.defaultZone;
    luxon.Settings.defaultZone = "Europe/Brussels";
    registerCleanup(() => {
        luxon.Settings.defaultLocale = originalLocale;
        luxon.Settings.defaultZone = originalZone;
    });
}

function makeMockLocation(hasListeners = () => true) {
    const locationLink = Object.assign(document.createElement("a"), {
        href: window.location.origin + window.location.pathname,
        assign(url) {
            this.href = url;
        },
        reload() {},
    });
    return new Proxy(locationLink, {
        get(target, p) {
            return target[p];
        },
        set(target, p, value) {
            if (p === "hash") {
                const oldURL = new URL(locationLink.href).toString();
                target[p] = value;
                const newURL = new URL(locationLink.href).toString();

                if (!hasListeners()) {
                    return true;
                }
                // the event hashchange must be triggered in a nonBlocking stack
                // https://html.spec.whatwg.org/multipage/browsing-the-web.html#scroll-to-fragid
                window.setTimeout(() => {
                    window.dispatchEvent(new HashChangeEvent("hashchange", { oldURL, newURL }));
                });
                return true;
            }
            target[p] = value;
            return true;
        },
    });
}

function patchBrowserWithCleanup() {
    const originalAddEventListener = browser.addEventListener;
    const originalRemoveEventListener = browser.removeEventListener;

    let hasHashChangeListeners = false;
    const mockLocation = makeMockLocation(() => hasHashChangeListeners);
    patchWithCleanup(
        browser,
        {
            // patch addEventListner to automatically remove listeners bound (via
            // browser.addEventListener) during a test (e.g. during the deployment of a service)
            addEventListener(evName) {
                if (evName === "hashchange") {
                    hasHashChangeListeners = true;
                }
                originalAddEventListener(...arguments);
                registerCleanup(() => {
                    originalRemoveEventListener(...arguments);
                });
            },
            navigator: {
                userAgent: browser.navigator.userAgent.replace(/\([^)]*\)/, "(X11; Linux x86_64)"),
            },
            // in tests, we never want to interact with the real url or reload the page
            location: mockLocation,
            history: {
                pushState(state, title, url) {
                    mockLocation.assign(url);
                },
                replaceState(state, title, url) {
                    mockLocation.assign(url);
                },
            },
            // in tests, we never want to interact with the real local/session storages.
            localStorage: makeRAMLocalStorage(),
            sessionStorage: makeRAMLocalStorage(),
        },
        { pure: true }
    );
}

function patchLegacyCoreBus() {
    // patch core.bus.on to automatically remove listners bound on the legacy bus
    // during a test (e.g. during the deployment of a service)
    const originalOn = core.bus.on.bind(core.bus);
    const originalOff = core.bus.off.bind(core.bus);
    patchWithCleanup(core.bus, {
        on() {
            originalOn(...arguments);
            registerCleanup(() => {
                originalOff(...arguments);
            });
        },
    });
}

function patchOdoo() {
    patchWithCleanup(odoo, {
        debug: "",
    });
}

function patchSessionInfo() {
    patchWithCleanup(sessionInfo, {
        cache_hashes: {
            load_menus: "161803",
            translations: "314159",
        },
        currencies: {
            1: { name: "USD", digits: [69, 2], position: "before", symbol: "$" },
            2: { name: "EUR", digits: [69, 2], position: "after", symbol: "€" },
        },
        user_context: {
            lang: "en",
            uid: 7,
            tz: "taht",
        },
        qweb: "owl",
        uid: 7,
        name: "Mitchell",
        username: "The wise",
        is_admin: true,
        is_system: true,
        partner_id: 7,
        // Commit: 3e847fc8f499c96b8f2d072ab19f35e105fd7749
        // to see what user_companies is
        user_companies: {
            allowed_companies: { 1: { id: 1, name: "Hermit" } },
            current_company: 1,
        },
        db: "test",
        server_version: "1.0",
        server_version_info: ["1.0"],
    });
}

export async function setupTests() {
    QUnit.testStart(() => {
        checkGlobalObjectsIntegrity();
        prepareRegistriesWithCleanup();
        prepareLegacyRegistriesWithCleanup();
        forceLocaleAndTimezoneWithCleanup();
        patchBrowserWithCleanup();
        patchLegacyCoreBus();
        patchOdoo();
        patchSessionInfo();
    });

    const templatesUrl = `/web/webclient/qweb/${new Date().getTime()}?bundle=web.assets_qweb`;
    const templates = await loadFile(templatesUrl);
    window.__OWL_TEMPLATES__ = processTemplates(templates);
    await Promise.all([whenReady(), legacyProm]);
}
