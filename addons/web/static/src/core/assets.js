/** @odoo-module **/

import { memoize } from "./utils/functions";
import { browser } from "./browser/browser";
import { registry } from "./registry";
import { session } from "@web/session";
import { Component, xml, onWillStart, App } from "@odoo/owl";

/**
 * This export is done only in order to modify the behavior of the exported
 * functions. This is done in order to be able to make a test environment.
 * Modules should only use the methods exported below.
 */
export const assets = {
    retries: {
        count: 3,
        delay: 5000,
        extraDelay: 2500,
    },
};

class AssetsLoadingError extends Error {}

/**
 * Loads the given url inside a script tag.
 *
 * @param {string} url the url of the script
 * @returns {Promise<true>} resolved when the script has been loaded
 */
assets.loadJS = memoize(function loadJS(url) {
    if (document.querySelector(`script[src="${url}"]`)) {
        // Already in the DOM and wasn't loaded through this function
        // Unfortunately there is no way to check whether a script has loaded
        // or not (which may not be the case for async/defer scripts)
        // so we assume it is.
        return Promise.resolve();
    }

    const scriptEl = document.createElement("script");
    scriptEl.type = "text/javascript";
    scriptEl.src = url;
    document.head.appendChild(scriptEl);
    return new Promise((resolve, reject) => {
        scriptEl.addEventListener("load", () => resolve(true));
        scriptEl.addEventListener("error", () => {
            reject(new AssetsLoadingError(`The loading of ${url} failed`));
        });
    });
});

/**
 * Loads the given url as a stylesheet.
 *
 * @param {string} url the url of the stylesheet
 * @returns {Promise<true>} resolved when the stylesheet has been loaded
 */
assets.loadCSS = memoize(function loadCSS(url, retryCount = 0) {
    if (document.querySelector(`link[href="${url}"]`)) {
        // Already in the DOM and wasn't loaded through this function
        // Unfortunately there is no way to check whether a link has loaded
        // or not (which may not be the case for async/defer stylesheets)
        // so we assume it is.
        return Promise.resolve();
    }
    const linkEl = document.createElement("link");
    linkEl.type = "text/css";
    linkEl.rel = "stylesheet";
    linkEl.href = url;
    const promise = new Promise((resolve, reject) => {
        linkEl.addEventListener("load", () => resolve(true));
        linkEl.addEventListener("error", async () => {
            if (retryCount < assets.retries.count) {
                await new Promise((resolve) =>
                    setTimeout(
                        resolve,
                        assets.retries.delay + assets.retries.extraDelay * retryCount
                    )
                );
                linkEl.remove();
                loadCSS(url, retryCount + 1)
                    .then(resolve)
                    .catch(reject);
            } else {
                reject(new AssetsLoadingError(`The loading of ${url} failed`));
            }
        });
    });
    document.head.appendChild(linkEl);
    return promise;
});

/**
 * Get the files information as descriptor object from a public asset template.
 *
 * @param {string} bundleName Name of the bundle containing the list of files
 * @returns {Promise<{cssLibs, cssContents, jsLibs, jsContents}>}
 */
assets.getBundle = memoize(async function getBundle(bundleName) {
    const url = new URL(`/web/bundle/${bundleName}`, location.origin);
    for (const [key, value] of Object.entries(session.bundle_params || {})) {
        url.searchParams.set(key, value);
    }
    const response = await browser.fetch(url.href);
    const json = await response.json();
    const assets = {
        cssLibs: [],
        cssContents: [], //todo cleanup
        jsLibs: [],
        jsContents: [],
    };
    for (const key in json) {
        const file = json[key];
        if (file.type === "link") {
            assets.cssLibs.push(file.src);
        } else if (file.type === "style") {
            assets.cssContents.push(file.content);
        } else {
            if (file.src) {
                assets.jsLibs.push(file.src);
            } else {
                assets.jsContents.push(file.content);
            }
        }
    }
    return assets;
});

/**
 * Loads the given js/css libraries and asset bundles. Note that no library or
 * asset will be loaded if it was already done before.
 *
 * @param {Object|string} desc
 * @param {Array<string|string[]>} [desc.assetLibs=[]]
 *      The list of assets to load. Each list item may be a string (the xmlID
 *      of the asset to load) or a list of strings. The first level is loaded
 *      sequentially (so use this if the order matters) while the assets in
 *      inner lists are loaded in parallel (use this for efficiency but only
 *      if the order does not matter, should rarely be the case for assets).
 * @param {string[]} [desc.cssLibs=[]]
 *      The list of CSS files to load. They will all be loaded in parallel but
 *      put in the DOM in the given order (only the order in the DOM is used
 *      to determine priority of CSS rules, not loaded time).
 * @param {Array<string|string[]>} [desc.jsLibs=[]]
 *      The list of JS files to load. Each list item may be a string (the URL
 *      of the file to load) or a list of strings. The first level is loaded
 *      sequentially (so use this if the order matters) while the files in inner
 *      lists are loaded in parallel (use this for efficiency but only
 *      if the order does not matter).
 * @param {string[]} [desc.cssContents=[]]
 *      List of inline styles to add after loading the CSS files.
 * @param {string[]} [desc.jsContents=[]]
 *      List of inline scripts to add after loading the JS files.
 *
 * @returns {Promise}
 */
assets.loadBundle = async function loadBundle(desc) {
    if (typeof desc === "string") {
        desc = await assets.getBundle(desc);
    }
    // Load css in parallel
    const promiseCSS = Promise.all((desc.cssLibs || []).map(assets.loadCSS)).then(() => {
        if (desc.cssContents && desc.cssContents.length) {
            const style = document.createElement("style");
            style.textContent = desc.cssContents.join("\n");
            document.head.appendChild(style);
        }
    });
    // Load JavaScript (don't wait for the css loading)
    for (const urlData of desc.jsLibs || []) {
        if (typeof urlData === "string") {
            // serial loading
            await assets.loadJS(urlData);
        } else {
            // parallel loading
            await Promise.all(urlData.map(loadJS));
        }
    }

    if (desc.jsContents && desc.jsContents.length) {
        const script = document.createElement("script");
        script.type = "text/javascript";
        script.textContent = desc.jsContents.join("\n");
        document.head.appendChild(script);
    }
    // Wait for the scc loading to be completed before loading the other bundle
    await promiseCSS;
    // Load other desc
    for (const bundleName of desc.assetLibs || []) {
        if (typeof bundleName === "string") {
            // serial loading
            await assets.loadBundle(bundleName);
        } else {
            // parallel loading
            await Promise.all(
                bundleName.map(async (bundleName) => {
                    return assets.loadBundle(bundleName);
                })
            );
        }
    }
    odoo.loader.checkAndReportErrors();
};

export const loadJS = function (url) {
    return assets.loadJS(url);
};
export const loadCSS = function (url) {
    return assets.loadCSS(url);
};
export const getBundle = function (bundleName) {
    return assets.getBundle(bundleName);
};
export const loadBundle = function (desc) {
    return assets.loadBundle(desc);
};

/**
 * Container dom containing all the owl templates that have been loaded.
 * This can be imported by the modules in order to use it when loading the
 * application and the components.
 */
export const templates = new DOMParser().parseFromString("<odoo/>", "text/xml");
/**
 * Each template is registered in xml_templates registry.
 * When a new template is added in the registry, it's also added to each owl App.
 */
registry.category("xml_templates").addEventListener("UPDATE", (ev) => {
    const { operation, value } = ev.detail;
    if (operation === "add") {
        const doc = new DOMParser().parseFromString(value, "text/xml");
        if (doc.querySelector("parsererror")) {
            // The generated error XML is non-standard so we log the full content to
            // ensure that the relevant info is actually logged.
            throw new Error(doc.querySelector("parsererror").textContent.trim());
        }

        for (const element of doc.querySelectorAll("templates > [t-name]")) {
            templates.documentElement.appendChild(element);
        }
        for (const app of App.apps) {
            app.addTemplates(templates, app);
        }
    }
});

/**
 * Utility component that loads an asset bundle before instanciating a component
 */
export class LazyComponent extends Component {
    setup() {
        onWillStart(async () => {
            await loadBundle(this.props.bundle);
            this.Component = registry.category("lazy_components").get(this.props.Component);
        });
    }
}
LazyComponent.template = xml`<t t-component="Component" t-props="props.props"/>`;
LazyComponent.props = {
    Component: String,
    bundle: String,
    props: { type: Object, optional: true },
};
