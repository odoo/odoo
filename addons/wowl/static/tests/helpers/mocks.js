/** @odoo-module **/
import { effectService } from "../../src/effects/effect_service";
import { makePushState, routeToUrl } from "../../src/services/router_service";
import { SIZES } from "../../src/services/device_service";
import { makeLocalization } from "../../src/services/localization_service";
// // -----------------------------------------------------------------------------
// // Mock Services
// // -----------------------------------------------------------------------------
export function makeFakeLocalizationService(config) {
  return {
    name: "localization",
    deploy: () => {
      return makeLocalization({
        langParams: (config && config.langParams) || {},
        terms: (config && config.terms) || {},
      });
    },
  };
}
/**
 * Simulate a fake user service.
 */
export function makeFakeUserService(values) {
  const { uid, name, username, is_admin, user_companies, partner_id, db } = odoo.session_info;
  const { user_context } = odoo.session_info;
  return {
    name: "user",
    deploy() {
      const result = {
        context: user_context,
        userId: uid,
        name: name,
        userName: username,
        isAdmin: is_admin,
        partnerId: partner_id,
        allowed_companies: user_companies.allowed_companies,
        current_company: user_companies.current_company,
        lang: user_context.lang,
        tz: "Europe/Brussels",
        db: db,
        showEffect: false,
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
  return async (...args) => {
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
  };
}
export function makeTestOdoo(config = {}) {
  return Object.assign({}, odoo, {
    browser: config.browser || {},
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
      user_companies: {
        allowed_companies: [[1, "Hermit"]],
        current_company: [1, "Hermit"],
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
    debugManagerRegistry: config.debugManagerRegistry,
    viewRegistry: config.viewRegistry,
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
//   // -----------------------------------------------------------------------------
//   // Low level API mocking
//   // -----------------------------------------------------------------------------
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
    name: "router",
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
      return {
        get current() {
          return getCurrent();
        },
        pushState: makePushState(env, getCurrent, doPush.bind(null, "push")),
        replaceState: makePushState(env, getCurrent, doPush.bind(null, "replace")),
        redirect: (params && params.redirect) || (() => {}),
      };
    },
  };
}
export function makeFakeDeviceService() {
  return {
    name: "device",
    deploy() {
      return {
        isSmall: false,
        isMobileOS: false,
        hasTouch: false,
        size: SIZES.LG,
        SIZES,
      };
    },
  };
}
export const fakeCookieService = {
  name: "cookie",
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
  name: "title",
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
    name: "download",
    deploy() {
      return async function (options) {
        if (callback) {
          return await callback(options);
        }
      };
    },
  };
}
export function makeFakeUIService(blockCallback, unblockCallback) {
  return {
    name: "ui",
    deploy() {
      function block() {
        if (blockCallback) {
          blockCallback();
        }
      }
      function unblock() {
        if (unblockCallback) {
          unblockCallback();
        }
      }
      return { block, unblock };
    },
  };
}
export function makeFakeNotificationService(createMock, closeMock) {
  return {
    name: "notification",
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
  localization: makeFakeLocalizationService,
  notifications: makeFakeNotificationService,
  router: makeFakeRouterService,
  rpc: makeFakeRPCService,
  title: () => fakeTitleService,
  ui: makeFakeUIService,
  user: makeFakeUserService,
};
