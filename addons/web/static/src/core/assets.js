/** @odoo-module **/

const { useEnv, onWillStart } = owl.hooks;
import { memoize } from "./utils/functions";
import { browser } from "./browser/browser";

class AssetsLoadingError extends Error {}

//------------------------------------------------------------------------------
// Types
//------------------------------------------------------------------------------

/**
 * An object describing a bundle to load
 * @typedef {Object} Bundle
 * @property {boolean} [templates] whether to load the qweb templates
 * @property {boolean} [js] whether to load the js from the bundle. Currently
 *      not implemented.
 * @property {boolean} [css] whether to load the css from the bundle. Currently
 *      not implemented.
 */

/**
 * An object describing a bundle to load. The keys are bundle names.
 * @typedef {Object<string, Bundle>} Bundles
 */

/**
 * An object describing a loaded bundle
 * @typedef {Object} LoadedBundle
 * @property {XMLDocument} templates an XML document containing the owl
 *      templates defined in that bundle
 */

/**
 * An object describing a loaded bundle. The keys are bundle names.
 * @typedef {Object<string, LoadedBundle>} LoadedBundles
 */

//------------------------------------------------------------------------------
// Helpers
//------------------------------------------------------------------------------

/**
 * Loads the given url inside a script tag.
 *
 * @param {string} url the url of the script
 * @returns {Promise} resolved when the script has been loaded
 */
const loadJS = memoize(function loadJS(url) {
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
        scriptEl.addEventListener("load", resolve);
        scriptEl.addEventListener("error", () => {
            reject(new AssetsLoadingError(`The loading of ${url} failed`));
        });
    });
});
/**
 * Loads the given url as a stylesheet.
 *
 * @param {string} url the url of the stylesheet
 * @returns {Promise} resolved when the stylesheet has been loaded
 */
const loadCSS = memoize(function loadCSS(url) {
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
        linkEl.addEventListener("load", resolve);
        linkEl.addEventListener("error", () => {
            reject(new AssetsLoadingError(`The loading of ${url} failed`));
        });
    });
});
/**
 * Loads the qweb templates from a given bundle name.
 *
 * @param {string} name the name of the bundle as declared in the manifest.
 * @returns {Promise<XMLDocument>} A Promise of an XML document containing the
 *      owl templates.
 */
export const loadBundleTemplates = memoize(async function loadBundleTemplates(name) {
    // TODO: quid of the "unique" in the URL? We can"t have one cache_hash
    // for each and every bundle I"m guessing.
    const bundleURL = `/web/webclient/qweb/${Date.now()}?bundle=${name}`;
    const templates = await (await browser.fetch(bundleURL)).text();
    return processTemplates(templates);
});

const bundlesCache = {};
/**
 * Loads a bundle.
 *
 * @param {string} name the name of the bundle to load
 * @param {Bundle} options parts of the bundle to load (see Bundle typedef)
 * @returns {Promise<LoadedBundle>}
 */
async function loadBundle(name, options) {
    const { templates } = options;
    if (!bundlesCache[name]) {
        bundlesCache[name] = { name };
    }
    if (templates && !bundlesCache[name].templates) {
        bundlesCache[name].templates = loadBundleTemplates(name);
    }
    // TODO: if ("js/css") {...} to support lazy loading js/css from bundles

    // Wait only for the requested keys
    const entries = await Promise.all(
        Object.keys(options).map(async (key) => [key, await bundlesCache[name][key]])
    );
    return Object.fromEntries(entries);
}

//------------------------------------------------------------------------------
// Exports
//------------------------------------------------------------------------------

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
    // owl environment's QWeb, and will be loaded separately.
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
 * @returns {Promise} Resolved when the contents of the asset is loaded
 */
export const loadPublicAsset = memoize(async function loadPublicAsset(xmlid, orm) {
    const xml = await orm.call("ir.ui.view", "render_public_asset", [xmlid]);
    const doc = new DOMParser().parseFromString(`<xml>${xml}</xml>`, "text/xml");
    return loadAssets({
        cssLibs: [...doc.querySelectorAll("link[href]")].map((node) => node.getAttribute("href")),
        jsLibs: [...doc.querySelectorAll("script[src]")].map((node) => node.getAttribute("src")),
    });
});
/**
 * Loads the given assets. Currently, when passing bundles, only the templates
 * key is supported, as loading a bundle's JS/CSS asynchronously requires some
 * groundwork.
 *
 * @param {Object} assets
 * @param {Bundles} [assets.bundles] an object describing the bundles to load.
 *      The keys are bundle names, and the values describe whether to load the
 *      templates, js and/or css from that bundle.
 * @param {string[]} [assets.jsLibs] urls of the javascript libraries to load
 * @param {string[]} [assets.cssLibs] urls of the css libraries to load
 * @returns {Promise<{[bundles: LoadedBundle[]]}>} An object describing the loaded
 *      assets. The js and css libs are loaded globally and will be loaded when
 *      this promise is resolved, the owl xml templates will be loaded in the
 *      `templates` key of each LoadedBundle object.
 */
export async function loadAssets(assets) {
    const proms = [];
    const loadedAssets = {};
    if ("bundles" in assets) {
        const bundles = Object.entries(assets.bundles);
        const bundlesProm = Promise.all(
            bundles.map(async ([name, options]) => [name, await loadBundle(name, options)])
        ).then((loadedBundles) => {
            loadedAssets.bundles = Object.fromEntries(loadedBundles);
        });
        proms.push(bundlesProm);
    }
    if ("jsLibs" in assets) {
        proms.push(Promise.all(assets.jsLibs.map(loadJS)));
    }
    if ("cssLibs" in assets) {
        proms.push(Promise.all(assets.cssLibs.map(loadCSS)));
    }
    await Promise.all(proms);
    return loadedAssets;
}
/**
 * Loads the given assets, and adds the loaded owl templates into the current
 * environment's qweb instance.
 *
 * @param {Object} assets
 * @param {Bundles} [assets.bundles] the bundles to load. See above typedef for
 *      details.
 * @param {string[]} [assets.jsLibs] urls of the javascript libraries to load
 * @param {string[]} [assets.cssLibs] urls of the css libraries to load
 */
export function useAssets(assets) {
    const env = useEnv();
    onWillStart(async () => {
        const loadedAssets = await loadAssets(assets);
        // TODO: { js, css } = loadedAssets when we support lazy loading js/css from bundles
        const { bundles } = loadedAssets;
        if (bundles) {
            const templateDocs = Object.values(bundles).map(({ templates }) => templates);
            // Some templates might already be defined by another bundle, but need
            // to be included in the current bundle for primary inherits to work.
            // We don't want to add those again. We also have to add them to qweb
            // one bundle at a time in case multiple bundles were specified that
            // include the same template (e.g. for inheritance)
            for (const xmlDoc of templateDocs) {
                for (const template of [...xmlDoc.querySelector("templates").children]) {
                    if (template.getAttribute("t-name") in env.qweb.templates) {
                        template.remove();
                    }
                }
                env.qweb.addTemplates(xmlDoc);
            }
        }
    });
}
