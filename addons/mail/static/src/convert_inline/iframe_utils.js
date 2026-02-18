import { loadBundle } from "@web/core/assets";

/**
 * Execute a callback once an iframe is ready/loaded in the DOM. The iframe must
 * have same origin sandbox policy enabled, and must be in the DOM (Chrome does
 * not dispatch the "load" event for an iframe without `src`).
 *
 * @param {HTMLIFrameElement} iframe
 * @param {Function} [callback]
 * @returns {Promise}
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
 * @param {Array<string>} bundles assets bundle names
 * @param {Object} [options] type of files to load
 * @returns {Promise}
 */
export function loadIframeBundles(iframe, bundles, { css = true, js = false } = {}) {
    return loadIframe(iframe, async () =>
        Promise.all(
            bundles.map(
                async (bundle) =>
                    await loadBundle(bundle, { targetDoc: iframe.contentDocument, css, js })
            )
        )
    );
}
