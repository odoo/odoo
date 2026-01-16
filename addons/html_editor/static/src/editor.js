import { PluginManager } from "./plugin_manager";
import { MAIN_PLUGINS } from "./plugin_sets";
import { createBaseContainer, SUPPORTED_BASE_CONTAINER_NAMES } from "./utils/base_container";
import { fillShrunkPhrasingParent, removeClass } from "./utils/dom";
import { isEmpty } from "./utils/dom_info";
import { fixInvalidHTML, initElementForEdition } from "./utils/sanitize";
import { setElementContent } from "@web/core/utils/html";

/** @typedef {import("plugins").EditorResources} EditorResources */
/** @typedef {import("plugins").GlobalResources} GlobalResources */
/** @typedef {keyof GlobalResources} GlobalResourcesId */
/**
 * @typedef {import("plugins").SharedMethods} SharedMethods
 * @typedef {import("plugins").PluginConstructor} PluginConstructor
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

 * @typedef { Object } EditorExtraConfig
 * @property { string } [content]
 * @property { boolean } [allowInlineAtRoot]
 * @property { string[] } [baseContainers]
 * @property { string[] } [classList]
 * @property { Object } [localOverlayContainers]
 * @property { Object } [embeddedComponentInfo]
 * @property { string } [direction="ltr"]
 * @property { Function } [onChange]
 * @property { Function } [onEditorReady]
 * @property { boolean } [dropImageAsAttachment]
 * @property { CollaborationConfig } [collaboration]
 * @property { Function } getRecordInfo
 * 
 * @typedef { PluginManagerConfig & EditorExtraConfig } EditorConfig
 *
 * @typedef { Object } EditorExtraContext
 * @property { EditorConfig } config
 * @property { Document } document
 * @property { HTMLElement } editable
 * @property { SharedMethods } dependencies
 * @property { import("./editor").EditorConfig } config
 * @property { import("services").ServiceFactories } services
 * @property { Editor['getResource'] } getResource
 * @property { Editor['dispatchTo'] } dispatchTo
 * @property { Editor['delegateTo'] } delegateTo
 */

/**
 * @typedef {((arg: {root: EditorContext["editable"]}) => void)[]} clean_for_save_handlers
 * @typedef {(() => void)[]} start_edition_handlers
 */

/**
 * Clean up DOM before taking into account for next history step remaining in
 * edit mode
 * @typedef {((root: EditorContext["editable"] | HTMLElement, stepState: "original"|"undo"|"redo"|"restore") => void)[]} normalize_handlers
 */

export class Editor extends PluginManager {
    /**
     * @param { EditorConfig } config
     */
    constructor(config, services) {
        super(config, services);
        this.pluginPropertyName = "__editor";
    }

    setup() {
        super.setup();
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
        editable.setAttribute("translate", "no");
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
        if (!this.config.Plugins) {
            this.config.Plugins = MAIN_PLUGINS;
        }
        super.preparePlugins();
    }

    startPlugins() {
        super.startPlugins();
        this.resources["normalize_handlers"].forEach((cb) => cb(this.editable));
        this.resources["start_edition_handlers"].forEach((cb) => cb());
    }

    /**
     * @return { EditorContext }
     */
    getPluginContext() {
        return Object.assign(super.getPluginContext(...arguments), {
            document: this.document,
            editable: this.editable,
        });
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
        this.isReady = false;
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
