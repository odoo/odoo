/** @odoo-module **/

import core, { _t } from "web.core";
import session from "web.session";
import { browser, makeRAMLocalStorage } from "@web/core/browser/browser";
import { patchTimeZone, patchWithCleanup } from "@web/../tests/helpers/utils";
import { legacyProm } from "web.test_legacy";
import { registerCleanup } from "./helpers/cleanup";
import { utils } from "./helpers/mock_env";
import { session as sessionInfo } from "@web/session";
import { prepareLegacyRegistriesWithCleanup } from "./helpers/legacy_env_utils";
import { config as transitionConfig } from "@web/core/transition";

transitionConfig.disabled = true;

import { patch } from "@web/core/utils/patch";
import { processTemplates } from "@web/core/assets";
const { App, whenReady, loadFile } = owl;

const { prepareRegistriesWithCleanup } = utils;

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
                const [, /* global */ keys] = objects[index];
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
    registerCleanup(() => {
        luxon.Settings.defaultLocale = originalLocale;
    });
    patchTimeZone(60);
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
            // Don't want original animation frames in tests
            requestAnimationFrame: (fn) => fn(),
            cancelAnimationFrame: () => {},
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

/**
 * Remove all given attributes from the templates and replace them by
 * data attributes (e.g. `src` to `data-src`, `alt` to `data-alt`).
 *
 * @param {string[]} attrs Attributes to replace by data-attributes.
 * @param {Document} templates Document containing the templates to
 * process.
 */
function removeUnwantedAttrsFromTemplates(templates, attrs) {
    function replaceAttr(attrName, prefix, element) {
        const attrKey = `${prefix}${attrName}`;
        const attrValue = element.getAttribute(attrKey);
        element.removeAttribute(attrKey);
        element.setAttribute(`${prefix}data-${attrName}`, attrValue);
    }
    const attrPrefixes = ["", "t-att-", "t-attf-"];
    for (const attrName of attrs) {
        for (const prefix of attrPrefixes) {
            for (const element of templates.querySelectorAll(`*[${prefix}${attrName}]`)) {
                replaceAttr(attrName, prefix, element);
            }
        }
    }
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
    // alt attribute causes issues with scroll tests. Indeed, alt is
    // displayed between the time we scroll programatically and the time
    // we assert for the scroll position. The src attribute is removed
    // as well to make sure images won't trigger a GET request on the
    // server.
    removeUnwantedAttrsFromTemplates(window.__OWL_TEMPLATES__, ["alt", "src"]);
    session.owlTemplates = window.__OWL_TEMPLATES__;
    await Promise.all([whenReady(), legacyProm]);

    // make sure images do not trigger a GET on the server
    new MutationObserver((mutations) => {
        const nodes = mutations.flatMap(({ target }) => {
            if (target.nodeName === "IMG" || target.nodeName === "IFRAME") {
                return target;
            }
            return [
                ...target.getElementsByTagName("img"),
                ...target.getElementsByTagName("iframe"),
            ];
        });
        for (const node of nodes) {
            const src = node.getAttribute("src");
            if (src && src !== "about:blank") {
                node.dataset.src = src;
                if (node.nodeName === "IMG") {
                    node.removeAttribute("src");
                } else {
                    node.setAttribute("src", "about:blank");
                }
                node.dispatchEvent(new Event("load"));
            }
        }
    }).observe(document.body, {
        subtree: true,
        childList: true,
        attributeFilter: ["src"],
    });
}
