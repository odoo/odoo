/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { routerService } from "@web/core/browser/router_service";
import { localization } from "@web/core/l10n/localization";
import { translatedTerms } from "@web/core/l10n/translation";
import { rpcService } from "@web/core/network/rpc_service";
import { userService } from "@web/core/user_service";
import { effectService } from "@web/webclient/effects/effect_service";
import { objectToUrlEncodedString } from "@web/core/utils/urls";
import { registerCleanup } from "./cleanup";
import { patchWithCleanup } from "./utils";
import { companyService } from "@web/webclient/company_service";
import { uiService } from "@web/core/ui_service";

const { Component } = owl;

// -----------------------------------------------------------------------------
// Mock Services
// -----------------------------------------------------------------------------

export const defaultLocalization = {
    dateFormat: "MM/dd/yyyy",
    timeFormat: "HH:mm:ss",
    dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
    decimalPoint: ".",
    direction: "ltr",
    grouping: [3, 0],
    multiLang: false,
    thousandsSep: ",",
    weekStart: 7,
};

/**
 * @param {Partial<typeof defaultLocalization>} [config]
 */
export function makeFakeLocalizationService(config = {}) {
    patchWithCleanup(localization, Object.assign({}, defaultLocalization, config));

    return {
        name: "localization",
        start: async (env) => {
            const _t = (str) => translatedTerms[str] || str;
            env._t = _t;
            env.qweb.translateFn = _t;
        },
    };
}

function buildMockRPC(mockRPC) {
    return async function (...args) {
        if (this instanceof Component && this.__owl__.status === 5) {
            return new Promise(() => {});
        }
        if (mockRPC) {
            return mockRPC(...args);
        }
    };
}

export function makeFakeRPCService(mockRPC) {
    return {
        name: "rpc",
        start() {
            return buildMockRPC(mockRPC);
        },
        specializeForComponent: rpcService.specializeForComponent,
    };
}

export function makeMockXHR(response, sendCb, def) {
    let MockXHR = function () {
        return {
            _loadListener: null,
            url: "",
            addEventListener(type, listener) {
                if (type === "load") {
                    this._loadListener = listener;
                }
            },
            open(method, url) {
                this.url = url;
            },
            setRequestHeader() {},
            async send(data) {
                if (sendCb) {
                    sendCb.call(this, JSON.parse(data));
                }
                if (def) {
                    await def;
                }
                this._loadListener();
            },
            response: JSON.stringify(response || ""),
        };
    };
    return MockXHR;
}

// -----------------------------------------------------------------------------
// Low level API mocking
// -----------------------------------------------------------------------------

export function makeMockFetch(mockRPC) {
    const _rpc = buildMockRPC(mockRPC);
    return async (input) => {
        let route = typeof input === "string" ? input : input.url;
        let params;
        if (route.includes("load_menus")) {
            const routeArray = route.split("/");
            params = {
                hash: routeArray.pop(),
            };
            route = routeArray.join("/");
        }
        let res;
        let status;
        try {
            res = await _rpc(route, params);
            status = 200;
        } catch (e) {
            status = 500;
        }
        const blob = new Blob([JSON.stringify(res || {})], { type: "application/json" });
        return new Response(blob, { status });
    };
}

/**
 * @param {Object} [params={}]
 * @param {Object} [params.onRedirect] hook on the "redirect" method
 * @returns {typeof routerService}
 */
export function makeFakeRouterService(params = {}) {
    return {
        start({ bus }) {
            const router = routerService.start(...arguments);
            bus.on("test:hashchange", null, (hash) => {
                browser.location.hash = objectToUrlEncodedString(hash);
            });
            registerCleanup(router.cancelPushes);
            patchWithCleanup(router, {
                async redirect() {
                    await this._super(...arguments);
                    if (params.onRedirect) {
                        params.onRedirect(...arguments);
                    }
                },
            });
            return router;
        },
    };
}

export const fakeCookieService = {
    start() {
        const cookie = {};
        return {
            get current() {
                return cookie;
            },
            setCookie(key, value) {
                if (value !== undefined) {
                    cookie[key] = value;
                }
            },
            deleteCookie(key) {
                delete cookie[key];
            },
        };
    },
};

export const fakeTitleService = {
    start() {
        let current = {};
        return {
            get current() {
                return JSON.stringify(current);
            },
            getParts() {
                return current;
            },
            setParts(parts) {
                current = Object.assign({}, current, parts);
            },
        };
    },
};

export function makeFakeNotificationService(mock) {
    return {
        start() {
            function add() {
                if (mock) {
                    return mock(...arguments);
                }
            }
            return {
                add,
            };
        },
    };
}

export function makeFakeDialogService(values = {}) {
    const open = values.open || (() => {});
    const close = values.close || (() => {});
    return {
        name: "dialog",
        start() {
            return {
                open,
                close,
            };
        },
    };
}

export const mocks = {
    company: () => companyService,
    cookie: () => fakeCookieService,
    effect: () => effectService, // BOI The real service ? Is this what we want ?
    localization: makeFakeLocalizationService,
    notifications: makeFakeNotificationService,
    router: makeFakeRouterService,
    rpc: makeFakeRPCService,
    title: () => fakeTitleService,
    ui: () => uiService,
    user: () => userService,
    dialog: makeFakeDialogService,
};
