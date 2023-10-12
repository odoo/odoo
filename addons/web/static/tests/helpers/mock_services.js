/** @odoo-module **/

import { Component, status } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { routerService } from "@web/core/browser/router_service";
import { effectService } from "@web/core/effects/effect_service";
import { localization } from "@web/core/l10n/localization";
import { rpcService } from "@web/core/network/rpc_service";
import { ormService } from "@web/core/orm_service";
import { overlayService } from "@web/core/overlay/overlay_service";
import { uiService } from "@web/core/ui/ui_service";
import { userService } from "@web/core/user_service";
import { objectToUrlEncodedString } from "@web/core/utils/urls";
import { ConnectionAbortedError } from "../../src/core/network/rpc_service";
import { registerCleanup } from "./cleanup";
import { patchWithCleanup } from "./utils";

// -----------------------------------------------------------------------------
// Mock Services
// -----------------------------------------------------------------------------

export const defaultLocalization = {
    dateFormat: "MM/dd/yyyy",
    timeFormat: "HH:mm:ss",
    dateTimeFormat: "MM/dd/yyyy HH:mm:ss",
    decimalPoint: ".",
    direction: "ltr",
    grouping: [],
    multiLang: false,
    thousandsSep: ",",
    weekStart: 7,
};

/**
 * @param {Partial<typeof defaultLocalization>} [config]
 */
export function makeFakeLocalizationService(config = {}) {
    patchWithCleanup(localization, { ...defaultLocalization, ...config });
    patchWithCleanup(luxon.Settings, { defaultNumberingSystem: "latn" });

    return {
        name: "localization",
        start: async (env) => {
            return localization;
        },
    };
}

function buildMockRPC(mockRPC) {
    return async function (...args) {
        if (this instanceof Component && status(this) === "destroyed") {
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
        start(env) {
            const rpcService = buildMockRPC(mockRPC);
            let nextId = 1;
            return function (route, params = {}, settings = {}) {
                let rejectFn;
                const data = {
                    id: nextId++,
                    jsonrpc: "2.0",
                    method: "call",
                    params: params,
                };
                env.bus.trigger("RPC:REQUEST", { data, settings });
                const rpcProm = new Promise((resolve, reject) => {
                    rejectFn = reject;
                    rpcService(...arguments)
                        .then((result) => {
                            env.bus.trigger("RPC:RESPONSE", { data, settings, result });
                            resolve(result);
                        })
                        .catch(reject);
                });
                rpcProm.abort = (rejectError = true) => {
                    if (rejectError) {
                        rejectFn(new ConnectionAbortedError("XmlHttpRequestError abort"));
                    }
                };
                return rpcProm;
            };
        },
        specializeForComponent: rpcService.specializeForComponent,
    };
}

export function makeMockXHR(response, sendCb, def) {
    const MockXHR = function () {
        return {
            _loadListener: null,
            url: "",
            addEventListener(type, listener) {
                if (type === "load") {
                    this._loadListener = listener;
                } else if (type === "error") {
                    this._errorListener = listener;
                }
            },
            set onload(listener) {
                this._loadListener = listener;
            },
            set onerror(listener) {
                this._errorListener = listener;
            },
            open(method, url) {
                this.url = url;
            },
            getResponseHeader() {},
            setRequestHeader() {},
            async send(data) {
                let listener = this._loadListener;
                if (sendCb) {
                    if (typeof data === "string") {
                        try {
                            data = JSON.parse(data);
                        } catch {
                            // Ignore
                        }
                    }
                    try {
                        await sendCb.call(this, data);
                    } catch {
                        listener = this._errorListener;
                    }
                }
                if (def) {
                    await def;
                }
                listener.call(this);
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
    return async (input, params) => {
        let route = typeof input === "string" ? input : input.url;
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
        } catch {
            status = 500;
        }
        const blob = new Blob([JSON.stringify(res || {})], { type: "application/json" });
        return new Response(blob, { status });
    };
}

/**
 * @param {Object} [params={}]
 * @returns {typeof routerService}
 */
export function makeFakeRouterService(params = {}) {
    return {
        start({ bus }) {
            const router = routerService.start(...arguments);
            bus.addEventListener("test:hashchange", (ev) => {
                const hash = ev.detail;
                browser.location.hash = objectToUrlEncodedString(hash);
            });
            registerCleanup(router.cancelPushes);
            return router;
        },
    };
}

export const fakeCommandService = {
    start() {
        return {
            add() {
                return () => {};
            },
            getCommands() {
                return [];
            },
            openPalette() {},
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

export const fakeColorSchemeService = {
    start() {
        return {
            switchToColorScheme() {},
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

export function makeFakeDialogService(addDialog) {
    return {
        start() {
            return {
                add: addDialog || (() => () => {}),
            };
        },
    };
}

export function makeFakeUserService(hasGroup = () => false) {
    return {
        ...userService,
        start() {
            const fakeUserService = userService.start(...arguments);
            fakeUserService.hasGroup = hasGroup;
            return fakeUserService;
        },
    };
}

export const fakeCompanyService = {
    start() {
        return {
            allowedCompanies: {},
            activeCompanyIds: [],
            currentCompany: {},
            setCompanies: () => {},
        };
    },
};

export function makeFakeBarcodeService() {
    return {
        start() {
            return {
                bus: {
                    async addEventListener() {},
                    async removeEventListener() {},
                },
            };
        },
    };
}

export function makeFakeHTTPService(getResponse, postResponse) {
    getResponse =
        getResponse ||
        ((route, readMethod) => {
            return readMethod === "json" ? {} : "";
        });
    postResponse =
        postResponse ||
        ((route, params, readMethod) => {
            return readMethod === "json" ? {} : "";
        });
    return {
        start() {
            return {
                async get(...args) {
                    return getResponse(...args);
                },
                async post(...args) {
                    return postResponse(...args);
                },
            };
        },
    };
}

function makeFakeActionService() {
    return {
        start() {
            return {
                doAction() {},
            };
        },
    };
}

export const mocks = {
    color_scheme: () => fakeColorSchemeService,
    company: () => fakeCompanyService,
    command: () => fakeCommandService,
    effect: () => effectService, // BOI The real service ? Is this what we want ?
    localization: makeFakeLocalizationService,
    notification: makeFakeNotificationService,
    router: makeFakeRouterService,
    rpc: makeFakeRPCService,
    title: () => fakeTitleService,
    ui: () => uiService,
    user: () => userService,
    dialog: makeFakeDialogService,
    orm: () => ormService,
    action: makeFakeActionService,
    overlay: () => overlayService,
};
