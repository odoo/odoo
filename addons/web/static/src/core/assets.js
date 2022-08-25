/** @odoo-module **/

import { memoize } from "./utils/functions";
import { browser } from "./browser/browser";
import { registry } from "./registry";

class AssetsLoadingError extends Error {}

/**
 * An object describing a bundle to load
 * @typedef {Object} BundleInfo
 * @property {'script'|'link'} [type] the type of file in this bundle
 * @property {string} [src] the url of the file for this bundle, for this type of file
 * @example `[{"type": "script", "src": "/web/assets/266-d34b0b4/documents_spreadsheet.o_spreadsheet.min.js"}]`
 */

/**
 * Loads the given url inside a script tag.
 *
 * @param {string} url the url of the script
 * @returns {Promise<true>} resolved when the script has been loaded
 */
export const loadJS = memoize(function loadJS(url) {
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
export const loadCSS = memoize(function loadCSS(url) {
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
    document.head.appendChild(linkEl);
    return new Promise(function (resolve, reject) {
        linkEl.addEventListener("load", () => resolve(true));
        linkEl.addEventListener("error", () => {
            reject(new AssetsLoadingError(`The loading of ${url} failed`));
        });
    });
});
/**
 * Loads the qweb templates from a given bundle name.
 * TODO: merge this into loadBundleDefinition?
 *
 * @param {string} bundle the name of the bundle as declared in the manifest.
 * @returns {Promise<XMLDocument|"">} A Promise of an XML document containing
 *      the owl templates or an empty string if the bundle has none.
 */
export const fetchAndProcessTemplates = memoize(async function fetchAndProcessTemplates(bundle) {
    // TODO: quid of the "unique" in the URL? We can't have one cache_hash
    // for each and every bundle I'm guessing.
    const bundleURL = `/web/webclient/qweb/${Date.now()}?bundle=${bundle}`;
    const templates = await (await browser.fetch(bundleURL)).text();
    if (!templates) {
        return "";
    }
    return processTemplates(templates);
});

/**
 * Loads the content definition of a bundle.
 *
 * @param {string} name the bundleName of the bundle as declared in the manifest.
 * @returns {Promise<BundleInfo[]>} A promise of the content definition of the bundle
 */
const loadBundleDefinition = memoize(async function (bundleName) {
    const request = await browser.fetch(`/web/bundle/${bundleName}`);
    return await request.json();
});

const bundlesCache = {};

/**
 * Loads a bundle.
 *
 * @param {string} name the name of the bundle to load
 * @param {owl.App} [app] the app in which the bundle's templates should be
 *      loaded. Defaults to the app that's written on the function itself, this
 *      is considered the main app, and should be written on the function by the
 *      code that bootstraps the app. In most cases, this will be the webclient,
 *      and is set in start.js
 * @returns {Promise<void>} a promise that is resolved after the bundle has been
 *      loaded.
 */
export async function loadBundle(name, app = loadBundle.app) {
    if (!bundlesCache[name]) {
        bundlesCache[name] = Promise.all([
            fetchAndProcessTemplates(name).then((templates) => app.addTemplates(templates, app)),
            loadBundleDefinition(name).then((bundleInfo) =>
                Promise.all([
                    ...bundleInfo.filter((i) => i.type === "script").map((i) => loadJS(i.src)),
                    ...bundleInfo.filter((i) => i.type === "link").map((i) => loadCSS(i.src)),
                ])
            ),
        ]).then(() => {});
    }

    return bundlesCache[name];
}

/**
 * Process the qweb templates to obtain only the owl templates. This function
 * does NOT register the templates into Owl.
 *
 * @param {string} templates An xml string describing templates
 * @returns {XMLDocument} An xml document containing only the owl templates
 */
export function processTemplates(templates) {
    const doc = new DOMParser().parseFromString(templates, "text/xml");
    // as we currently have two qweb engines (owl and legacy), owl templates are
    // flagged with attribute `owl="1"`. The following lines removes the "owl"
    // attribute from the templates, so that it doesn't appear in the DOM. We
    // also remove the non-owl templates, as those shouldn't be loaded in the
    // owl application, and will be loaded separately.
    for (const template of [...doc.querySelector("templates").children]) {
        if (template.hasAttribute("owl")) {
            template.removeAttribute("owl");
        } else {
            template.remove();
        }
    }
    return doc;
}

/**
 * Renders a public asset template and loads the libraries defined inside of it.
 * Only loads js and css, template declarations will be ignored. Only loads
 * scripts and styles that are defined in script src and link href, ignores
 * inline scripts and styles.
 *
 * @deprecated
 * @param {string} xmlid The xmlid of the template that defines the public asset
 * @param {ORM} orm An ORM object capable of calling methods on models
 * @returns {Promise<void>} Resolved when the contents of the asset is loaded
 */
export const loadPublicAsset = memoize(async function loadPublicAsset(xmlid, orm) {
    const xml = await orm.call("ir.ui.view", "render_public_asset", [xmlid]);
    const doc = new DOMParser().parseFromString(`<xml>${xml}</xml>`, "text/xml");
    return Promise.all([
        ...[...doc.querySelectorAll("link[href]")].map((el) => loadCSS(el.getAttribute("href"))),
        ...[...doc.querySelectorAll("script[src]")].map((el) => loadJS(el.getAttribute("src"))),
    ]);
});

const { Component, xml, onWillStart } = owl;
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
