/** @odoo-module **/

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

const cacheMap = new Map();

class AssetsLoadingError extends Error {}

/**
 * Loads the given url inside a script tag.
 *
 * @param {string} url the url of the script
 * @returns {Promise<true>} resolved when the script has been loaded
 */
assets.loadJS = async function loadJS(url) {
    if (cacheMap.has(url)) {
        return cacheMap.get(url);
    }
    const scriptEl = document.createElement("script");
    scriptEl.type = "text/javascript";
    scriptEl.src = url;
    const promise = new Promise((resolve, reject) => {
        scriptEl.onload = () => resolve(true);
        scriptEl.onerror = () => {
            cacheMap.delete(url);
            reject(new AssetsLoadingError(`The loading of ${url} failed`));
        };
    });
    cacheMap.set(url, promise);
    document.head.appendChild(scriptEl);
    return promise;
};

/**
 * Loads the given url as a stylesheet.
 *
 * @param {string} url the url of the stylesheet
 * @returns {Promise<true>} resolved when the stylesheet has been loaded
 */
assets.loadCSS = async function loadCSS(url, retryCount = 0) {
    if (cacheMap.has(url)) {
        return cacheMap.get(url);
    }
    const linkEl = document.createElement("link");
    linkEl.type = "text/css";
    linkEl.rel = "stylesheet";
    linkEl.href = url;
    const promise = new Promise((resolve, reject) => {
        linkEl.onload = () => resolve(true);
        linkEl.onerror = async () => {
            cacheMap.delete(url);
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
        };
    });
    cacheMap.set(url, promise);
    document.head.appendChild(linkEl);
    return promise;
};

/**
 * Get the files information as descriptor object from a public asset template.
 *
 * @param {string} bundleName Name of the bundle containing the list of files
 * @returns {Promise<{cssLibs, jsLibs}>}
 */
assets.getBundle = async function getBundle(bundleName) {
    if (cacheMap.has(bundleName)) {
        return cacheMap.get(bundleName);
    }
    const url = new URL(`/web/bundle/${bundleName}`, location.origin);
    for (const [key, value] of Object.entries(session.bundle_params || {})) {
        url.searchParams.set(key, value);
    }
    const response = await browser.fetch(url.href);
    const json = await response.json();
    const assets = {
        cssLibs: [],
        jsLibs: [],
    };
    for (const key in json) {
        const file = json[key];
        if (file.type === "link" && file.src) {
            assets.cssLibs.push(file.src);
        } else if (file.type === "script" && file.src) {
            assets.jsLibs.push(file.src);
        }
    }
    cacheMap.set(bundleName, assets);
    return assets;
};

/**
 * Loads the given js/css libraries and asset bundles. Note that no library or
 * asset will be loaded if it was already done before.
 *
 * @param {string} bundleName
 * @returns {Promise[]}
 */
assets.loadBundle = async function loadBundle(bundleName) {
    if (typeof bundleName === "string") {
        const desc = await assets.getBundle(bundleName);
        return Promise.all([
            ...(desc.cssLibs || []).map(assets.loadCSS),
            ...(desc.jsLibs || []).map(assets.loadJS),
        ]);
    } else {
        throw new Error(
            `loadBundle(bundleName:string) accepts only bundleName argument as a string ! Not ${JSON.stringify(
                bundleName
            )} as ${typeof bundleName}`
        );
    }
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
export const loadBundle = function (bundleName) {
    return assets.loadBundle(bundleName);
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
