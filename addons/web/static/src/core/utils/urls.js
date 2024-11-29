import { session } from "@web/session";
import { browser } from "../browser/browser";
import { shallowEqual } from "@web/core/utils/objects";
const { DateTime } = luxon;

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
 * @param {string} model
 * @param {number} id
 * @param {string} field
 * @param {Object} [options]
 * @param {string} [options.filename]
 * @param {number} [options.height]
 * @param {string|import('luxon').DateTime} [options.unique]
 * @param {number} [options.width]
 */
export function imageUrl(model, id, field, { filename, height, unique, width } = {}) {
    let route = `/web/image/${model}/${id}/${field}`;
    if (width && height) {
        route = `${route}/${width}x${height}`;
    }
    if (filename) {
        route = `${route}/${filename}`;
    }
    const urlParams = {};
    if (unique) {
        if (unique instanceof DateTime) {
            urlParams.unique = unique.ts;
        } else {
            const dateTimeFromUnique = DateTime.fromSQL(unique);
            if (dateTimeFromUnique.isValid) {
                urlParams.unique = dateTimeFromUnique.ts;
            } else if (typeof unique === "string" && unique.length > 0) {
                urlParams.unique = unique;
            }
        }
    }
    return url(route, urlParams);
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
    browser.location.assign(_url.href);
}

/**
 * This function compares two URLs. It doesn't care about the order of the search parameters.
 *
 * @param {string} _url1
 * @param {string} _url2
 * @returns {boolean} true if the urls are identical, false otherwise
 */
export function compareUrls(_url1, _url2) {
    const url1 = new URL(_url1);
    const url2 = new URL(_url2);
    return (
        url1.origin === url2.origin &&
        url1.pathname === url2.pathname &&
        shallowEqual(
            Object.fromEntries(url1.searchParams),
            Object.fromEntries(url2.searchParams)
        ) &&
        url1.hash === url2.hash
    );
}
