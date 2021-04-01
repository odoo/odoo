/** @odoo-module **/

import { effectService } from "../../src/effects/effect_service";
import { makePreProcessQuery, makePushState, routeToUrl } from "../../src/services/router_service";
import { SIZES } from "../../src/services/ui_service";
import { rpcService } from "../../src/services/rpc_service";
import { localization } from "../../src/localization/localization_settings";
import { patch, unpatch } from "../../src/utils/patch";
import { registerCleanup } from "./cleanup";
import { translatedTerms } from "../../src/localization/translation";
import { computeAllowedCompanyIds, makeSetCompanies } from "../../src/services/user_service";

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

export function makeFakeLocalizationService(config) {
  patch(localization, "localization.mock.patch", defaultLocalization);
  registerCleanup(() => unpatch(localization, "localization.mock.patch"));

  return {
    name: "localization",
    deploy: async (env) => {
      const _t = (str) => translatedTerms[str] || str;
      env._t = _t;
      env.qweb.translateFn = _t;
    },
  };
}

/**
 * Simulate a fake user service.
 */
export function makeFakeUserService(values) {
  const sessionInfo = {};
  Object.assign(sessionInfo, odoo.session_info, values && values.session_info);
  const { uid, name, username, is_admin, user_companies, partner_id, user_context } = sessionInfo;
  return {
    name: "user",
    deploy(env) {
      let allowedCompanies = computeAllowedCompanyIds();
      const setCompanies = makeSetCompanies(() => allowedCompanies);
      const context = {
        ...user_context,
        get allowed_company_ids() {
          return allowedCompanies;
        },
      };
      const result = {
        context,
        userId: uid,
        name: name,
        userName: username,
        isAdmin: is_admin,
        partnerId: partner_id,
        allowed_companies: user_companies.allowed_companies,
        get current_company() {
          return user_companies.allowed_companies[allowedCompanies[0]];
        },
        lang: user_context.lang,
        tz: "Europe/Brussels",
        get db() {
          const res = {
            name: sessionInfo.db,
          };
          if ("dbuuid" in sessionInfo) {
            res.uuid = sessionInfo.dbuuid;
          }
          return res;
        },
        showEffect: false,
        setCompanies(mode, companyId) {
          allowedCompanies = setCompanies(mode, companyId);
        },
      };
      Object.assign(result, values);
      return result;
    },
  };
}

/*export function makeFakeMenusService(menuData?: MenuData): Service<MenuService> {
  const _menuData = menuData || {
    root: { id: "root", children: [1], name: "root" },
    1: { id: 1, children: [], name: "App0" },
  };
  return {
    name: "menus",
    deploy() {
      const menusService = {
        getMenu(menuId: keyof MenuData) {
          return _menuData![menuId];
        },
        getApps() {
          return this.getMenu("root").children.map((mid) => this.getMenu(mid));
        },
        getAll() {
          return Object.values(_menuData);
        },
        getMenuAsTree(menuId: keyof MenuData) {
          const menu = this.getMenu(menuId) as MenuTree;
          if (!menu.childrenTree) {
            menu.childrenTree = menu.children.map((mid: Menu["id"]) => this.getMenuAsTree(mid));
          }
          return menu;
        },
      };
      return menusService;
    },
  };
}*/

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
    deploy() {
      return buildMockRPC(mockRPC);
    },
    specializeForComponent: rpcService.specializeForComponent,
  };
}

export function makeTestOdoo(config = {}) {
  return Object.assign({}, odoo, {
    browser: {},
    debug: config.debug,
    session_info: {
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
    },
    serviceRegistry: config.serviceRegistry,
    mainComponentRegistry: config.mainComponentRegistry,
    actionRegistry: config.actionRegistry,
    systrayRegistry: config.systrayRegistry,
    errorDialogRegistry: config.errorDialogRegistry,
    userMenuRegistry: config.userMenuRegistry,
    debugRegistry: config.debugRegistry,
    viewRegistry: config.viewRegistry,
    commandCategoryRegistry: config.commandCategoryRegistry,
  });
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

function stripUndefinedQueryKey(query) {
  const keyValArray = Array.from(Object.entries(query)).filter(([k, v]) => v !== undefined);
  // transform to Object.fromEntries in es > 2019
  const newObj = {};
  keyValArray.forEach(([k, v]) => {
    newObj[k] = v;
  });
  return newObj;
}

function getRoute(route) {
  route.hash = stripUndefinedQueryKey(route.hash);
  route.search = stripUndefinedQueryKey(route.search);
  return route;
}

export function makeFakeRouterService(params) {
  let _current = {
    pathname: "test.wowl",
    search: {},
    hash: {},
  };
  if (params && params.initialRoute) {
    Object.assign(_current, params.initialRoute);
  }
  let current = getRoute(_current);
  return {
    deploy(env) {
      function loadState(hash) {
        current.hash = hash;
        env.bus.trigger("ROUTE_CHANGE");
      }
      env.bus.on("test:hashchange", null, loadState);
      function getCurrent() {
        return current;
      }
      function doPush(mode = "push", route) {
        const oldUrl = routeToUrl(current);
        const newRoute = getRoute(route);
        const newUrl = routeToUrl(newRoute);
        if (params && params.onPushState && oldUrl !== newUrl) {
          params.onPushState(mode, route.hash);
        }
        current = newRoute;
      }
      const preProcessQuery = makePreProcessQuery(getCurrent);
      return {
        get current() {
          return getCurrent();
        },
        pushState: makePushState(getCurrent, doPush.bind(null, "push"), preProcessQuery),
        replaceState: makePushState(getCurrent, doPush.bind(null, "replace"), preProcessQuery),
        redirect: (params && params.redirect) || (() => {}),
      };
    },
  };
}

export function makeFakeUIService(values) {
  const defaults = {
    bus: new owl.core.EventBus(),
    activateElement: () => {},
    deactivateElement: () => {},
    block: () => {},
    unblock: () => {},
    isSmall: false,
    size: SIZES.LG,
    SIZES,
  };
  return {
    deploy(env) {
      const res = Object.assign(defaults, values);
      Object.defineProperty(env, "isSmall", {
        get() {
          return res.isSmall;
        },
      });
      return res;
    },
  };
}

export const fakeCookieService = {
  deploy() {
    const cookie = {};
    return {
      get current() {
        return cookie;
      },
      setCookie(key, value, ttl) {
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
  deploy() {
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

export function makeFakeDownloadService(callback) {
  return {
    deploy() {
      return async function (options) {
        if (callback) {
          return await callback(options);
        }
      };
    },
  };
}

export function makeFakeNotificationService(createMock, closeMock) {
  return {
    deploy() {
      function create() {
        if (createMock) {
          return createMock(...arguments);
        }
      }
      function close() {
        if (closeMock) {
          return closeMock(...arguments);
        }
      }
      return {
        create,
        close,
      };
    },
  };
}

export const mocks = {
  cookie: () => fakeCookieService,
  download: makeFakeDownloadService,
  effect: () => effectService,
  notifications: makeFakeNotificationService,
  router: makeFakeRouterService,
  rpc: makeFakeRPCService,
  title: () => fakeTitleService,
  user: makeFakeUserService,
};
