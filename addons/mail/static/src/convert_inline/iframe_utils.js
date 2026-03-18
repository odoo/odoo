import { loadBundle } from "@web/core/assets";

/**
 * Execute a callback once an iframe is ready/loaded in the DOM. The iframe must
 * have same origin sandbox policy enabled, and must be in the DOM (Chrome does
 * not dispatch the "load" event for an iframe without `src`).
 *
 * @template [I=HTMLIFrameElement]
 * @template [T=any]
 * @param {I} iframe
 * @param {(iframe: I) => T} [callback]
 * @returns {Promise<T>}
 */
export function loadIframe(iframe, callback = () => {}) {
    const { promise: iframeLoaded, resolve } = Promise.withResolvers();
    const onIframeLoaded = () => {
        if (iframe.isConnected) {
            resolve(callback(iframe));
        }
        resolve(null);
    };
    if (iframe.contentDocument?.readyState === "complete") {
        // Browsers like Chrome don't make use of the load event for iframes without `src`
        onIframeLoaded();
    } else {
        // Browsers like Firefox only make iframe document available after dispatching "load"
        iframe.addEventListener("load", () => onIframeLoaded(), { once: true });
    }
    return iframeLoaded;
}

/**
 * Loads asset bundles inside an iframe. The iframe must have same origin
 * sandbox policy enabled, and must be in the DOM (Chrome does not dispatch the
 * "load" event for an iframe without `src`).
 *
 * @param {HTMLIFrameElement} iframe
 * @param {string[]} bundles assets bundle names
 * @param {Parameters<loadBundle>[1]} [options] type of files to load
 */
export function loadIframeBundles(iframe, bundles, options) {
    const bundleOptions = { js: false, targetDoc: iframe.contentDocument, ...options };
    return loadIframe(iframe, () =>
        Promise.all(bundles.map((bundle) => loadBundle(bundle, bundleOptions)))
    );
}
