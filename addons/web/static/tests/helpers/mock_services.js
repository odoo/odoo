/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { routerService } from "@web/core/browser/router_service";
import { effectService } from "@web/core/effects/effect_service";
import { localization } from "@web/core/l10n/localization";
import { ConnectionAbortedError, rpcBus, rpc } from "@web/core/network/rpc";
import { ormService } from "@web/core/orm_service";
import { overlayService } from "@web/core/overlay/overlay_service";
import { uiService } from "@web/core/ui/ui_service";
import { user, _makeUser } from "@web/core/user";
import { objectToUrlEncodedString } from "@web/core/utils/urls";
import { registerCleanup } from "./cleanup";
import { patchWithCleanup } from "./utils";
import { session } from "@web/session";

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

export function patchRPCWithCleanup(mockRPC = () => {}) {
    let nextId = 1;
    patchWithCleanup(rpc, {
        _rpc: function (route, params = {}, settings = {}) {
            let rejectFn;
            const data = {
                id: nextId++,
                jsonrpc: "2.0",
                method: "call",
                params: params,
            };
            rpcBus.trigger("RPC:REQUEST", { data, url: route, settings });
            const rpcProm = new Promise((resolve, reject) => {
                rejectFn = reject;
                Promise.resolve(mockRPC(...arguments))
                    .then((result) => {
                        rpcBus.trigger("RPC:RESPONSE", { data, settings, result });
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
        },
    });
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
            res = await mockRPC(route, params);
            status = 200;
        } catch {
            status = 500;
        }
        const blob = new Blob([JSON.stringify(res || {})], { type: "application/json" });
        const response = new Response(blob, { status });
        // Mock some functions of the Response API to make them almost synchronous (micro-tick level)
        // as their native implementation is async (tick level), which can lead to undeterministic
        // errors as it breaks the hypothesis that calling nextTick after fetching data is enough
        // to see the result rendered in the DOM.
        response.json = () => Promise.resolve(JSON.parse(JSON.stringify(res || {})));
        response.text = () => Promise.resolve(String(res || {}));
        response.blob = () => Promise.resolve(blob);
        return response;
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

export function makeMockedUser(hasGroup) {
    hasGroup = hasGroup || user.hasGroup;
    patchWithCleanup(user, _makeUser());
    patchWithCleanup(user, { hasGroup });
}

export function patchUserContextWithCleanup(patch) {
    patchWithCleanup(session.user_context, patch);
    makeMockedUser(user.hasGroup); // keep the mocked hasGroup
}

export function patchUserWithCleanup(patch) {
    patchWithCleanup(user, patch);
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
    title: () => fakeTitleService,
    ui: () => uiService,
    dialog: makeFakeDialogService,
    orm: () => ormService,
    action: makeFakeActionService,
    overlay: () => overlayService,
};
