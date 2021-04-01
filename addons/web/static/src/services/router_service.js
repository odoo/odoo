/** @odoo-module **/

import { browser } from "../core/browser";
import { serviceRegistry } from "../webclient/service_registry";
import { shallowEqual } from "../utils/objects";
import { objectToUrlEncodedString } from "../utils/urls";

function parseString(str) {
  const parts = str.split("&");
  const result = {};
  for (let part of parts) {
    const [key, value] = part.split("=");
    result[key] = decodeURIComponent(value || "");
  }
  return result;
}

function sanitizeHash(hash) {
  return Object.fromEntries(Object.entries(hash).filter(([_, v]) => v !== undefined));
}

export function parseHash(hash) {
  return hash === "#" || hash === "" ? {} : parseString(hash.slice(1));
}

export function parseSearchQuery(search) {
  return search === "" ? {} : parseString(search.slice(1));
}

export function routeToUrl(route) {
  const search = objectToUrlEncodedString(route.search);
  const hash = objectToUrlEncodedString(route.hash);
  return route.pathname + (search ? "?" + search : "") + (hash ? "#" + hash : "");
}

export function redirect(env, url, wait) {
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

/**
 * @param {function} getCurrent function that returns the current route
 * @returns {function} function to compute the next hash
 */
export function makePreProcessQuery(getCurrent) {
  const lockedKeys = new Set();
  return (hash) => {
    const newHash = {};
    Object.keys(hash).forEach((key) => {
      if (lockedKeys.has(key)) {
        return;
      }
      const k = key.split(" ");
      let value;
      if (k.length === 2) {
        value = hash[key];
        key = k[1];
        if (k[0] === "lock") {
          lockedKeys.add(key);
        } else if (k[0] === "unlock") {
          lockedKeys.delete(key);
        } else {
          return;
        }
      }
      newHash[key] = value || hash[key];
    });
    const current = getCurrent();
    Object.keys(current.hash).forEach((key) => {
      if (lockedKeys.has(key) && !(key in newHash)) {
        newHash[key] = current.hash[key];
      }
    });
    return newHash;
  };
}

function makeRouter(env) {
  let bus = env.bus;
  let current = getRoute();
  window.addEventListener("hashchange", () => {
    current = getRoute();
    bus.trigger("ROUTE_CHANGE");
  });

  function doPush(mode = "push", route) {
    if (!shallowEqual(route.hash, current.hash)) {
      const url = location.origin + routeToUrl(route);
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

  const preProcessQuery = makePreProcessQuery(getCurrent);
  return {
    get current() {
      return getCurrent();
    },
    pushState: makePushState(getCurrent, doPush.bind(null, "push"), preProcessQuery),
    replaceState: makePushState(getCurrent, doPush.bind(null, "replace"), preProcessQuery),
    redirect: (url, wait) => redirect(env, url, wait),
  };
}

export function makePushState(getCurrent, doPush, preProcessQuery) {
  let _replace = false;
  let timeoutId;
  let tempHash;
  return (hash, replace = false) => {
    clearTimeout(timeoutId);
    hash = preProcessQuery(hash);
    _replace = _replace || replace;
    tempHash = Object.assign(tempHash || {}, hash);
    timeoutId = setTimeout(() => {
      tempHash = sanitizeHash(tempHash);
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
