/** @odoo-module **/

import { serviceRegistry } from "./service_registry";

function parseString(str) {
  const parts = str.split("&");
  const result = {};
  for (let part of parts) {
    const [key, value] = part.split("=");
    result[key] = decodeURIComponent(value || "");
  }
  return result;
}

export function parseHash(hash) {
  return hash === "#" || hash === "" ? {} : parseString(hash.slice(1));
}

export function parseSearchQuery(search) {
  return search === "" ? {} : parseString(search.slice(1));
}

function toString(query) {
  return Object.entries(query)
    .filter(([k, v]) => v !== undefined)
    .map(([k, v]) => (v ? `${k}=${encodeURIComponent(v)}` : k))
    .join("&");
}

export function routeToUrl(route) {
  const search = toString(route.search);
  const hash = toString(route.hash);
  return route.pathname + (search ? "?" + search : "") + (hash ? "#" + hash : "");
}

export function redirect(env, url, wait) {
  const browser = odoo.browser;
  const load = () => browser.location.assign(url);
  if (wait) {
    const wait_server = function () {
      env.services
        .rpc("/web/webclient/version_info", {})
        .then(load)
        .catch(() => browser.setTimeout(wait_server, 250));
    };
    browser.setTimeout(wait_server, 1000);
  } else {
    load();
  }
}

function getRoute() {
  const { pathname, search, hash } = window.location;
  const searchQuery = parseSearchQuery(search);
  const hashQuery = parseHash(hash);
  return { pathname, search: searchQuery, hash: hashQuery };
}

function makeRouter(env) {
  let bus = env.bus;
  let current = getRoute();
  window.addEventListener("hashchange", () => {
    current = getRoute();
    bus.trigger("ROUTE_CHANGE");
  });

  function doPush(mode = "push", route) {
    const url = location.origin + routeToUrl(route);
    if (url !== window.location.href) {
      if (mode === "push") {
        window.history.pushState({}, url, url);
      } else {
        window.history.replaceState({}, url, url);
      }
    }
    current = getRoute();
  }

  function getCurrent() {
    return current;
  }

  return {
    get current() {
      return getCurrent();
    },
    pushState: makePushState(env, getCurrent, doPush.bind(null, "push")),
    replaceState: makePushState(env, getCurrent, doPush.bind(null, "replace")),
    redirect: (url, wait) => redirect(env, url, wait),
  };
}

export function makePushState(env, getCurrent, doPush) {
  let _replace = false;
  let timeoutId;
  let tempHash;
  return (hash, replace = false) => {
    clearTimeout(timeoutId);
    _replace = _replace || replace;
    tempHash = Object.assign(tempHash || {}, hash);
    timeoutId = setTimeout(() => {
      const current = getCurrent();
      if (!_replace) {
        tempHash = Object.assign({}, current.hash, tempHash);
      }
      const route = Object.assign({}, current, { hash: tempHash });
      doPush(route);
      tempHash = undefined;
      timeoutId = undefined;
      _replace = false;
    });
  };
}

export const routerService = {
  name: "router",
  deploy(env) {
    return makeRouter(env);
  },
};

export function objectToQuery(obj) {
  const query = {};
  Object.entries(obj).forEach(([k, v]) => {
    query[k] = v ? `${v}` : v;
  });
  return query;
}

serviceRegistry.add("router", routerService);