import { resourceSequenceSymbol, withSequence } from "@html_editor/utils/resource";
import { getCSSRules, toInline } from "@mail/views/web/fields/html_mail_field/convert_inline";
import { Deferred } from "@web/core/utils/concurrency";

/**
 * @typedef { typeof import("@html_editor/plugin").Plugin } PluginConstructor
 *
 * @see MailHtmlConverter.toInline
 * @typedef { Object } MailHtmlConversionConfig
 * @property { HTMLElement } container **Empty** element in browsing context with relevant stylesheets for the conversion.
 *            its content will be managed by the MailHtmlConverter during the conversion, and emptied at the end.
 * @property { HTMLElement } reference DIV element containing the editor html mail value output. Will be inserted in the
 *            container and used for style measurements.
 * @property { PluginConstructor[] } Plugins Plugins to use for html conversion. @see registry TODO EGGMAIL: add relevant registry keys
 * @property { Object } [resources] custom resources used by Plugins
 */

function sortPlugins(plugins) {
    const initialPlugins = new Set(plugins);
    const inResult = new Set();
    // need to sort them
    const result = [];
    let P;

    function findPlugin() {
        for (const P of initialPlugins) {
            if (P.dependencies.every((dep) => inResult.has(dep))) {
                initialPlugins.delete(P);
                return P;
            }
        }
    }
    while ((P = findPlugin())) {
        inResult.add(P.id);
        result.push(P);
    }
    if (initialPlugins.size) {
        const messages = [];
        for (const P of initialPlugins) {
            messages.push(
                `"${P.id}" is missing (${P.dependencies
                    .filter((d) => !inResult.has(d))
                    .join(", ")})`
            );
        }
        throw new Error(`Missing dependencies:  ${messages.join(", ")}`);
    }
    return result;
}

export class MailHtmlConverter {
    constructor(services) {
        this.isDestroyed = false;
        this.services = services;
        this.setup();
    }

    setup() {
        this.outputPromise = new Deferred();
        this.config = {};
        this.resources = null;
        this.plugins = [];
        /** @type { HTMLElement } **/
        this.editable = null;
        /** @type { Document } **/
        this.document = null;
        this.containerDocument = null;
        /** @ts-ignore  @type { SharedMethods } **/
        this.shared = {};
        this.output = {};
        this.cleanups = [];
        this.iframe = null;
        this.iframeLoaded = new Deferred();
    }

    setupContainer() {
        const container = this.config.container;
        const containerStyle = container.getAttribute("style");
        const containerAriaHidden = container.getAttribute("aria-hidden");
        // The container width is set to 1320px to ensure the email reference
        // content can grow as much as it should.
        container.setAttribute(
            "style",
            `position: absolute !important;
            top: 0 !important;
            left: -9999px !important;
            pointer-events: none !important;
            visibility: hidden !important;
            min-width: 1320px !important;`
        );
        container.setAttribute("aria-hidden", "true");
        this.containerDocument = container.ownerDocument;
        this.setupEditableIframe();
        const reference = this.config.reference;
        const referenceStyle = reference.getAttribute("style");
        reference.setAttribute("style", `width: 100% !important`);
        container.replaceChildren(reference, this.iframe);
        this.cleanups.push(() => {
            if (containerStyle === "") {
                container.removeAttribute("style");
            } else {
                container.setAttribute("style", containerStyle);
            }
            if (containerAriaHidden === "") {
                container.removeAttribute("aria-hidden");
            } else {
                container.setAttribute("aria-hidden", containerAriaHidden);
            }
            if (referenceStyle === "") {
                reference.removeAttribute("style");
            } else {
                reference.setAttribute("style", referenceStyle);
            }
            container.replaceChildren();
        });
    }

    setupContainerIframe() {
        const containerIframe = this.containerDocument.defaultView.frameElement;
        const iframeStyle = containerIframe.getAttribute("style");
        // It is primordial that the iframe be visible during the operation.
        // The iframe dimensions must also be under control to trigger media
        // queries for the "desktop" version of the email.
        containerIframe.setAttribute(
            "style",
            `display: block !important;
            width: 1320px !important;
            min-width: 1320px !important;
            height: 1000px !important;
            min-height: 1000px !important;`
        );
        this.cleanups.push(() => {
            if (iframeStyle === "") {
                containerIframe.removeAttribute("style");
            } else {
                containerIframe.setAttribute("style", iframeStyle);
            }
        });
    }

    setupEditableIframe() {
        this.iframe = this.containerDocument.createElement("IFRAME");
        this.iframe.setAttribute("sandbox", "allow-same-origin");
        this.iframe.setAttribute("style", `width: 100% !important`);
    }

    setupEditable() {
        this.editable = this.iframe.contentDocument.body;
        this.document = this.editable.ownerDocument;
        // The iframe body must exactly have the iframe horizontal dimensions.
        this.editable.setAttribute(
            "style",
            `margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;`
        );
        this.iframeLoaded.resolve();
    }

    cleanup() {
        for (const cleanup of this.cleanups.reverse()) {
            cleanup();
        }
    }

    /**
     * @param {MailHtmlConversionConfig} config
     */
    async convertToEmailHtml(config) {
        if (this.isDestroyed) {
            return;
        }
        this.setup();
        this.config = config;
        this.setupContainer();
        this.setupContainerIframe();
        if (this.iframe.contentDocument.readyState === "complete") {
            this.setupEditable();
        } else {
            this.iframe.addEventListener("load", () => this.setupEditable(), { once: true });
        }
        await this.iframeLoaded;
        this.preparePlugins();
        this.startPlugins();

        await this.htmlConversion();

        this.outputPromise.resolve(this.output);
        this.cleanup();
    }

    createResources() {
        const resources = {};

        function registerResources(obj) {
            for (const key in obj) {
                if (!(key in resources)) {
                    resources[key] = [];
                }
                resources[key].push(obj[key]);
            }
        }
        if (this.config.resources) {
            registerResources(this.config.resources);
        }
        for (const plugin of this.plugins) {
            if (plugin.resources) {
                registerResources(plugin.resources);
            }
        }

        for (const key in resources) {
            const resource = resources[key]
                .flat()
                .map((r) => {
                    const isObjectWithSequence =
                        typeof r === "object" && r !== null && resourceSequenceSymbol in r;
                    return isObjectWithSequence ? r : withSequence(10, r);
                })
                .sort((a, b) => a[resourceSequenceSymbol] - b[resourceSequenceSymbol])
                .map((r) => r.object);

            resources[key] = resource;
            Object.freeze(resources[key]);
        }

        return Object.freeze(resources);
    }

    destroy() {
        let plugin;
        while ((plugin = this.plugins.pop())) {
            plugin.destroy();
        }
        this.cleanup();
        this.isDestroyed = true;
    }

    getContent() {
        return this.getElContent().innerHTML;
    }

    getElContent() {
        return this.editable.cloneNode(true);
    }

    /**
     * @param {string} resourceId
     * @returns {Array}
     */
    getResource(resourceId) {
        return this.resources[resourceId] || [];
    }

    async htmlConversion() {
        // Old toInline
        // TODO EGGMAIL: adapt usage, use plugin instead of old method
        const cssRules = getCSSRules(this.containerDocument);
        await toInline(this.config.reference, cssRules);

        // // 1 load async content (i.e. image) for final dimensions
        // await Promise.all(
        //     this.getResource("load_reference_content_handlers")
        //         .map((job) => job({ root: this.config.reference }))
        //         .flat()
        // );
    }

    preparePlugins() {
        const Plugins = sortPlugins(this.config.Plugins);
        this.config = Object.assign({}, ...Plugins.map((P) => P.defaultConfig), this.config);
        const plugins = new Map();
        for (const P of Plugins) {
            if (P.id === "") {
                throw new Error(`Missing plugin id (class ${P.name})`);
            }
            if (plugins.has(P.id)) {
                throw new Error(`Duplicate plugin id: ${P.id}`);
            }
            const imports = {};
            for (const dep of P.dependencies) {
                if (plugins.has(dep)) {
                    imports[dep] = {};
                    for (const h of plugins.get(dep).shared) {
                        imports[dep][h] = this.shared[dep][h];
                    }
                } else {
                    throw new Error(`Missing dependency for plugin ${P.id}: ${dep}`);
                }
            }
            plugins.set(P.id, P);
            const plugin = new P(this.document, this.editable, imports, this.config, this.services);
            this.plugins.push(plugin);
            const exports = {};
            for (const h of P.shared) {
                if (!(h in plugin)) {
                    throw new Error(`Missing helper implementation: ${h} in plugin ${P.id}`);
                }
                exports[h] = plugin[h].bind(plugin);
            }
            this.shared[P.id] = exports;
        }
        const resources = this.createResources();
        for (const plugin of this.plugins) {
            plugin._resources = resources;
        }
        this.resources = resources;
    }

    startPlugins() {
        for (const plugin of this.plugins) {
            plugin.setup();
        }
    }
}
