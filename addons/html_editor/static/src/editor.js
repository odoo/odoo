import { MAIN_PLUGINS } from "./plugin_sets";
import { createBaseContainer, SUPPORTED_BASE_CONTAINER_NAMES } from "./utils/base_container";
import { fillShrunkPhrasingParent, removeClass } from "./utils/dom";
import { isEmpty } from "./utils/dom_info";
import { resourceSequenceSymbol, withSequence } from "./utils/resource";
import { fixInvalidHTML, initElementForEdition } from "./utils/sanitize";
import { setElementContent } from "@web/core/utils/html";

/**
 * @typedef { import("./plugin_sets").SharedMethods } SharedMethods
 * @typedef {typeof import("./plugin").Plugin} PluginConstructor
 **/

/**
 * @typedef { Object } CollaborationConfig
 * @property { string } collaboration.peerId
 * @property { Object } collaboration.busService
 * @property { Object } collaboration.collaborationChannel
 * @property { String } collaboration.collaborationChannel.collaborationModelName
 * @property { String } collaboration.collaborationChannel.collaborationFieldName
 * @property { Number } collaboration.collaborationChannel.collaborationResId
 * @property { 'start' | 'focus' } [collaboration.collaborativeTrigger]

 * @typedef { Object } EditorConfig
 * @property { string } [content]
 * @property { boolean } [allowInlineAtRoot]
 * @property { string[] } [baseContainers]
 * @property { PluginConstructor[] } [Plugins]
 * @property { string[] } [classList]
 * @property { Object } [localOverlayContainers]
 * @property { Object } [embeddedComponentInfo]
 * @property { Object } [resources]
 * @property { string } [direction="ltr"]
 * @property { Function } [onChange]
 * @property { Function } [onEditorReady]
 * @property { boolean } [dropImageAsAttachment]
 * @property { CollaborationConfig } [collaboration]
 * @property { Function } getRecordInfo
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

export class Editor {
    /**
     * @param { EditorConfig } config
     */
    constructor(config, services) {
        this.isReady = false;
        this.isDestroyed = false;
        this.config = config;
        this.services = services;
        this.resources = null;
        this.plugins = [];
        /** @type { HTMLElement } **/
        this.editable = null;
        /** @type { Document } **/
        this.document = null;
        /** @ts-ignore  @type { SharedMethods } **/
        this.shared = {};
    }

    attachTo(editable) {
        if (this.isDestroyed || this.editable) {
            throw new Error("Cannot re-attach an editor");
        }
        this.editable = editable;
        this.document = editable.ownerDocument;
        this.preparePlugins();
        if ("content" in this.config) {
            setElementContent(editable, fixInvalidHTML(this.config.content));
            if (isEmpty(editable)) {
                const baseContainer = createBaseContainer(
                    this.config.baseContainers[0],
                    this.document
                );
                fillShrunkPhrasingParent(baseContainer);
                editable.replaceChildren(baseContainer);
            }
        }
        editable.setAttribute("contenteditable", true);
        initElementForEdition(editable, { allowInlineAtRoot: !!this.config.allowInlineAtRoot });
        editable.classList.add("odoo-editor-editable");
        if (this.config.classList) {
            editable.classList.add(...this.config.classList);
        }
        if (this.config.height) {
            editable.style.height = this.config.height;
        }
        if (
            !this.config.baseContainers.every((name) =>
                SUPPORTED_BASE_CONTAINER_NAMES.includes(name)
            )
        ) {
            throw new Error(
                `Invalid baseContainers: ${this.config.baseContainers.join(
                    ", "
                )}. Supported: ${SUPPORTED_BASE_CONTAINER_NAMES.join(", ")}`
            );
        }
        this.startPlugins();
        this.isReady = true;
        this.config.onEditorReady?.();
    }

    preparePlugins() {
        const Plugins = sortPlugins(this.config.Plugins || MAIN_PLUGINS);
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
        this.resources["normalize_handlers"].forEach((cb) => cb(this.editable));
        this.resources["start_edition_handlers"].forEach((cb) => cb());
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

    /**
     * @param {string} resourceId
     * @returns {Array}
     */
    getResource(resourceId) {
        return this.resources[resourceId] || [];
    }

    /**
     * Executes the functions registered under resourceId with the given
     * arguments.
     *
     * @param {string} resourceId
     * @param  {...any} args The arguments to pass to the handlers
     */
    dispatchTo(resourceId, ...args) {
        this.getResource(resourceId).forEach((handler) => handler(...args));
    }

    getContent() {
        return this.getElContent().innerHTML;
    }

    getElContent() {
        const el = this.editable.cloneNode(true);
        this.resources["clean_for_save_handlers"].forEach((cb) => cb({ root: el }));
        return el;
    }

    destroy(willBeRemoved) {
        if (this.editable) {
            let plugin;
            while ((plugin = this.plugins.pop())) {
                plugin.destroy();
            }
            this.shared = {};
            if (!willBeRemoved) {
                // we only remove class/attributes when necessary. If we know that the editable
                // element will be removed, no need to make changes that may require the browser
                // to recompute the layout
                this.editable.removeAttribute("contenteditable");
                removeClass(this.editable, "odoo-editor-editable");
            }
            this.editable = null;
        }
        this.isDestroyed = true;
    }
}
