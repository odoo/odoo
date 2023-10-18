/** @odoo-module **/

import { assets, templates } from "@web/core/assets";
import { browser, makeRAMLocalStorage } from "@web/core/browser/browser";
import { patchTimeZone, patchWithCleanup } from "@web/../tests/helpers/utils";
import { memoize } from "@web/core/utils/functions";
import { registerCleanup } from "./helpers/cleanup";
import { prepareRegistriesWithCleanup } from "./helpers/mock_env";
import { session as sessionInfo } from "@web/session";
import { config as transitionConfig } from "@web/core/transition";
import { loadLanguages } from "@web/core/l10n/translation";

transitionConfig.disabled = true;

import { patch } from "@web/core/utils/patch";
import { App, EventBus, whenReady } from "@odoo/owl";
import { currencies } from "@web/core/currency";
import { cookie } from "@web/core/browser/cookie";

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

function patchOwlApp() {
    patchWithCleanup(App.prototype, {
        destroy() {
            if (!this.destroyed) {
                super.destroy(...arguments);
                this.destroyed = true;
            }
        },
    });
}

function patchCookie() {
    const cookieJar = {};

    patchWithCleanup(cookie, {
        get _cookieMonster() {
            return Object.entries(cookieJar)
                .filter(([, value]) => value !== "kill")
                .map((cookie) => cookie.join("="))
                .join("; ");
        },
        set _cookieMonster(value) {
            const cookies = value.split("; ");
            for (const cookie of cookies) {
                const [key, value] = cookie.split(/=(.*)/);
                if (!["path", "max-age"].includes(key)) {
                    cookieJar[key] = value;
                }
            }
        },
    });
}

function patchBrowserWithCleanup() {
    const originalAddEventListener = browser.addEventListener;
    const originalRemoveEventListener = browser.removeEventListener;
    const originalSetTimeout = browser.setTimeout;
    const originalClearTimeout = browser.clearTimeout;
    const originalSetInterval = browser.setInterval;
    const originalClearInterval = browser.clearInterval;

    let hasHashChangeListeners = false;
    let nextAnimationFrameHandle = 1;
    const animationFrameHandles = new Set();
    const mockLocation = makeMockLocation(() => hasHashChangeListeners);
    patchWithCleanup(browser, {
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
        // patch setTimeout to automatically remove timeouts bound (via
        // browser.setTimeout) during a test (e.g. during the deployment of a service)
        setTimeout() {
            const timeout = originalSetTimeout(...arguments);
            registerCleanup(() => {
                originalClearTimeout(timeout);
            });
            return timeout;
        },
        // patch setInterval to automatically remove callbacks registered (via
        // browser.setInterval) during a test (e.g. during the deployment of a service)
        setInterval() {
            const interval = originalSetInterval(...arguments);
            registerCleanup(() => {
                originalClearInterval(interval);
            });
            return interval;
        },
        // patch BeforeInstallPromptEvent to prevent the installPrompt service to return an uncontrolled
        // canPromptToInstall value depending the browser settings (we ensure the value is always falsy)
        BeforeInstallPromptEvent: undefined,
        navigator: {
            mediaDevices: browser.navigator.mediaDevices,
            permissions: browser.navigator.permissions,
            userAgent: browser.navigator.userAgent.replace(/\([^)]*\)/, "(X11; Linux x86_64)"),
            sendBeacon: () => {},
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
        requestAnimationFrame: (fn) => {
            const handle = nextAnimationFrameHandle++;
            animationFrameHandles.add(handle);

            Promise.resolve().then(() => {
                if (animationFrameHandles.has(handle)) {
                    fn(16);
                }
            });

            return handle;
        },
        cancelAnimationFrame: (handle) => {
            animationFrameHandles.delete(handle);
        },
        // BroadcastChannels need to be closed to be garbage collected
        BroadcastChannel: class SelfClosingBroadcastChannel extends BroadcastChannel {
            constructor() {
                super(...arguments);
                registerCleanup(() => this.close());
            }
        },
    });
}

function patchBodyAddEventListener() {
    // In some cases, e.g. tooltip service, event handlers are registered on document.body and not
    // browser, because the events we listen to aren't triggered on window. We want to clear those
    // handlers as well after each test.
    const originalBodyAddEventListener = document.body.addEventListener;
    const originalBodyRemoveEventListener = document.body.removeEventListener;
    document.body.addEventListener = function () {
        originalBodyAddEventListener.call(this, ...arguments);
        registerCleanup(() => {
            originalBodyRemoveEventListener.call(this, ...arguments);
        });
    };
    registerCleanup(() => {
        document.body.addEventListener = originalBodyAddEventListener;
    });
}

function patchOdoo() {
    patchWithCleanup(odoo, {
        debug: "",
    });
}

function cleanLoadedLanguages() {
    registerCleanup(() => {
        loadLanguages.installedLanguages = null;
    });
}

function patchSessionInfo() {
    patchWithCleanup(sessionInfo, {
        cache_hashes: {
            load_menus: "161803",
            translations: "314159",
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
        server_version_info: [1, 0, 0, "final", 0, ""],
    });
    patchWithCleanup(currencies, {
        1: { name: "USD", digits: [69, 2], position: "before", symbol: "$" },
        2: { name: "EUR", digits: [69, 2], position: "after", symbol: "€" },
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
function removeUnwantedAttrsFromTemplates(attrs) {
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

function patchAssets() {
    const { getBundle, loadJS, loadCSS } = assets;
    patch(assets, {
        getBundle: memoize(async function (xmlID) {
            console.log(
                "%c[assets] fetch libs from xmlID: " + xmlID,
                "color: #66e; font-weight: bold;"
            );
            return getBundle(xmlID);
        }),
        loadJS: memoize(async function (ressource) {
            if (ressource.match(/\/static(\/\S+\/|\/)libs?/)) {
                console.log(
                    "%c[assets] fetch (mock) JS ressource: " + ressource,
                    "color: #66e; font-weight: bold;"
                );
                return Promise.resolve();
            }
            console.log(
                "%c[assets] fetch JS ressource: " + ressource,
                "color: #66e; font-weight: bold;"
            );
            return loadJS(ressource);
        }),
        loadCSS: memoize(async function (ressource) {
            if (ressource.match(/\/static(\/\S+\/|\/)libs?/)) {
                console.log(
                    "%c[assets] fetch (mock) CSS ressource: " + ressource,
                    "color: #66e; font-weight: bold;"
                );
                return Promise.resolve();
            }
            console.log(
                "%c[assets] fetch CSS ressource: " + ressource,
                "color: #66e; font-weight: bold;"
            );
            return loadCSS(ressource);
        }),
    });
}

function patchEventBus() {
    patchWithCleanup(EventBus.prototype, {
        addEventListener() {
            super.addEventListener(...arguments);
            registerCleanup(() => this.removeEventListener(...arguments));
        },
    });
}

export async function setupTests() {
    // uncomment to debug memory leaks in qunit suite
    // if (window.gc) {
    //     let memoryBeforeModule;
    //     QUnit.moduleStart(({ tests }) => {
    //         if (tests.length) {
    //             window.gc();
    //             memoryBeforeModule = window.performance.memory.usedJSHeapSize;
    //         }
    //     });
    //     QUnit.moduleDone(({ name }) => {
    //         if (memoryBeforeModule) {
    //             window.gc();
    //             const afterGc = window.performance.memory.usedJSHeapSize;
    //             console.log(
    //                 `MEMINFO - After suite "${name}" - after gc: ${afterGc} delta: ${
    //                     afterGc - memoryBeforeModule
    //                 }`
    //             );
    //             memoryBeforeModule = null;
    //         }
    //     });
    // }

    QUnit.testStart(() => {
        prepareRegistriesWithCleanup();
        forceLocaleAndTimezoneWithCleanup();
        cleanLoadedLanguages();
        patchBrowserWithCleanup();
        patchCookie();
        patchBodyAddEventListener();
        patchEventBus();
        patchOdoo();
        patchSessionInfo();
        patchOwlApp();
    });

    await whenReady();

    // alt attribute causes issues with scroll tests. Indeed, alt is
    // displayed between the time we scroll programatically and the time
    // we assert for the scroll position. The src attribute is removed
    // as well to make sure images won't trigger a GET request on the
    // server.
    // Clean up templates that have already been added.
    removeUnwantedAttrsFromTemplates(["alt", "src"]);
    patchAssets();

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
