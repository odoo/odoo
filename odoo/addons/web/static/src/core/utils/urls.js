/** @odoo-module **/

import { session } from "@web/session";
import { browser } from "../browser/browser";

export class RedirectionError extends Error {}

/**
 * Transforms a key value mapping to a string formatted as url hash, e.g.
 * {a: "x", b: 2} -> "a=x&b=2"
 *
 * @param {Object} obj
 * @returns {string}
 */
export function objectToUrlEncodedString(obj) {
    return Object.entries(obj)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v || "")}`)
        .join("&");
}

/**
 * Gets the origin url of the page, or cleans a given one
 *
 * @param {string} [origin]: a given origin url
 * @return {string} a cleaned origin url
 */
export function getOrigin(origin) {
    if (origin) {
        // remove trailing slashes
        origin = origin.replace(/\/+$/, "");
    } else {
        const { host, protocol } = browser.location;
        origin = `${protocol}//${host}`;
    }
    return origin;
}

/**
 * @param {string} route: the relative route, or absolute in the case of cors urls
 * @param {object} [queryParams]: parameters to be appended as the url's queryString
 * @param {object} [options]
 * @param {string} [options.origin]: a precomputed origin
 */
export function url(route, queryParams, options = {}) {
    const origin = getOrigin(options.origin ?? session.origin);
    if (!route) {
        return origin;
    }

    let queryString = objectToUrlEncodedString(queryParams || {});
    queryString = queryString.length > 0 ? `?${queryString}` : queryString;

    // Compare the wanted url against the current origin
    let prefix = ["http://", "https://", "//"].some(
        (el) => route.length >= el.length && route.slice(0, el.length) === el
    );
    prefix = prefix ? "" : origin;
    return `${prefix}${route}${queryString}`;
}

/**
 * Gets dataURL (base64 data) from the given file or blob.
 * Technically wraps FileReader.readAsDataURL in Promise.
 *
 * @param {Blob | File} file
 * @returns {Promise} resolved with the dataURL, or rejected if the file is
 *  empty or if an error occurs.
 */
export function getDataURLFromFile(file) {
    if (!file) {
        return Promise.reject();
    }
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.addEventListener("load", () => {
            // Handle Chrome bug that creates invalid data URLs for empty files
            if (reader.result === "data:") {
                resolve(`data:${file.type};base64,`);
            } else {
                resolve(reader.result);
            }
        });
        reader.addEventListener("abort", reject);
        reader.addEventListener("error", reject);
        reader.readAsDataURL(file);
    });
}

/**
 * Safely redirects to the given url within the same origin.
 *
 * @param {string} url
 * @throws {RedirectionError} if the given url has a different origin
 */
export function redirect(url) {
    const { origin, pathname } = browser.location;
    const _url = new URL(url, `${origin}${pathname}`);
    if (_url.origin !== origin) {
        throw new RedirectionError("Can't redirect to another origin");
    }
    browser.location = _url.href;
}
