/** @odoo-module **/

import { browser } from "../core/browser";

/**
 * Trasnforms a key value mapping to a string formatted as url hash, e.g.
 * {a: "x", b: 2} -> "a=x&b=2"
 *
 * @param {Object} obj
 * @returns {string}
 */
export function objectToUrlEncodedString(obj) {
  return Object.entries(obj)
    .map(([k, v]) => (v ? `${k}=${encodeURIComponent(v)}` : k))
    .join("&");
}

/**
 * @param {string} [origin] if not given, defaults to the actual location origin
 * @returns {Object} with keys
 *   - origin: sanitized given origin, or actual origin
 *   - url: function to build complete urls based on a route and params
 */
export function urlBuilder(origin) {
  if (origin) {
    // remove trailing slashes
    origin = origin.replace(/\/+$/, "");
  } else {
    const { host, protocol } = browser.location;
    origin = `${protocol}//${host}`;
  }

  function url(route, params) {
    params = params || {};
    let queryString = objectToUrlEncodedString(params);
    queryString = queryString.length > 0 ? `?${queryString}` : queryString;

    // Compare the wanted url against the current origin
    let prefix = ["http://", "https://", "//"].some(
      (el) => route.length >= el.length && route.slice(0, el.length) === el
    );
    prefix = prefix ? "" : origin;
    return `${prefix}${route}${queryString}`;
  }

  return { origin, url };
}
