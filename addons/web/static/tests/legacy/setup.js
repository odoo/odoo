/** @odoo-module alias=@web/../tests/setup default=false */

import { assets } from "@web/core/assets";
import { user, _makeUser } from "@web/core/user";
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
import { router } from "@web/core/browser/router";
import { registerTemplateProcessor } from "@web/core/templates";

function forceLocaleAndTimezoneWithCleanup() {
    const originalLocale = luxon.Settings.defaultLocale;
    luxon.Settings.defaultLocale = "en";
    registerCleanup(() => {
        luxon.Settings.defaultLocale = originalLocale;
    });
    patchTimeZone(60);
}

function makeMockLocation() {
    return Object.assign(document.createElement("a"), {
        href: window.location.origin + "/odoo",
        assign(url) {
            this.href = url;
        },
        reload() {},
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

    let nextAnimationFrameHandle = 1;
    const animationFrameHandles = new Set();
    const mockLocation = makeMockLocation();
    let historyStack = [[null, mockLocation.href]];
    let currentHistoryStack = 0;
    patchWithCleanup(browser, {
        // patch addEventListner to automatically remove listeners bound (via
        // browser.addEventListener) during a test (e.g. during the deployment of a service)
        addEventListener() {
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
        // patch BeforeInstallPromptEvent to prevent the pwa service to return an uncontrolled
        // canPromptToInstall value depending the browser settings (we ensure the value is always falsy)
        BeforeInstallPromptEvent: undefined,
        navigator: {
            mediaDevices: browser.navigator.mediaDevices,
            permissions: browser.navigator.permissions,
            userAgent: browser.navigator.userAgent.replace(/\([^)]*\)/, "(X11; Linux x86_64)"),
            sendBeacon: () => {
                throw new Error("sendBeacon called in test but not mocked");
            },
        },
        // in tests, we never want to interact with the real url or reload the page
        location: mockLocation,
        history: {
            pushState(state, title, url) {
                historyStack = historyStack.slice(0, currentHistoryStack + 1);
                historyStack.push([state, url]);
                currentHistoryStack++;
                mockLocation.assign(url);
            },
            replaceState(state, title, url) {
                historyStack[currentHistoryStack] = [state, url];
                mockLocation.assign(url);
            },
            back() {
                currentHistoryStack--;
                const [state, url] = historyStack[currentHistoryStack];
                if (!url) {
                    throw new Error("there is no history");
                }
                mockLocation.assign(url);
                window.dispatchEvent(new PopStateEvent("popstate", { state }));
            },
            forward() {
                currentHistoryStack++;
                const [state, url] = historyStack[currentHistoryStack];
                if (!url) {
                    throw new Error("No more history");
                }
                mockLocation.assign(url);
                window.dispatchEvent(new PopStateEvent("popstate", { state }));
            },
            get length() {
                return historyStack.length;
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
        // XHR: we don't want tests to do real RPCs
        XMLHttpRequest: class MockXHR {
            constructor() {
                throw new Error("XHR not patched in a test. Consider using patchRPCWithCleanup.");
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
        info: {
            db: sessionInfo.db,
            server_version: sessionInfo.server_version,
            server_version_info: sessionInfo.server_version_info,
            isEnterprise: sessionInfo.server_version_info.slice(-1)[0] === "e",
        },
    });
}

function cleanLoadedLanguages() {
    registerCleanup(() => {
        loadLanguages.installedLanguages = null;
    });
}

function patchSessionInfo() {
    patchWithCleanup(sessionInfo, {
        qweb: "owl",
        // Commit: 3e847fc8f499c96b8f2d072ab19f35e105fd7749
        // to see what user_companies is
        user_companies: {
            allowed_companies: { 1: { id: 1, name: "Hermit" } },
            current_company: 1,
        },
        user_context: {
            lang: "en",
            tz: "taht",
        },
        db: "test",
        registry_hash: "05500d71e084497829aa807e3caa2e7e9782ff702c15b2f57f87f2d64d049bd0",
        is_admin: true,
        is_system: true,
        username: "thewise@odoo.com",
        name: "Mitchell",
        partner_id: 7,
        uid: 7,
        server_version: "1.0",
        server_version_info: [1, 0, 0, "final", 0, ""],
    });
    const mockedUser = _makeUser(sessionInfo);
    patchWithCleanup(user, mockedUser);
    patchWithCleanup(user, { hasGroup: () => Promise.resolve(false) });
    patchWithCleanup(currencies, {
        1: { name: "USD", digits: [69, 2], position: "before", symbol: "$" },
        2: { name: "EUR", digits: [69, 2], position: "after", symbol: "€" },
    });
}

function replaceAttr(attrName, prefix, element) {
    const attrKey = `${prefix}${attrName}`;
    const attrValue = element.getAttribute(attrKey);
    element.removeAttribute(attrKey);
    element.setAttribute(`${prefix}data-${attrName}`, attrValue);
}

registerTemplateProcessor((template) => {
    // We remove all the attributes `src` and `alt` from the template and replace them by
    // data attributes (e.g. `src` to `data-src`, `alt` to `data-alt`).
    // alt attribute causes issues with scroll tests. Indeed, alt is
    // displayed between the time we scroll programmatically and the time
    // we assert for the scroll position. The src attribute is removed
    // as well to make sure images won't trigger a GET request on the
    // server.
    for (const attrName of ["alt", "src"]) {
        for (const prefix of ["", "t-att-", "t-attf-"]) {
            for (const element of template.querySelectorAll(`*[${prefix}${attrName}]`)) {
                replaceAttr(attrName, prefix, element);
            }
        }
    }
});

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
        registerCleanup(router.cancelPushes);
        patchCookie();
        patchBodyAddEventListener();
        patchEventBus();
        patchSessionInfo();
        patchOdoo();
        patchOwlApp();
    });

    await whenReady();
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
