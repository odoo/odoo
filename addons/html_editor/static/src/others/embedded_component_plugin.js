import { nodeToTree } from "@html_editor/core/history_plugin";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { memoize } from "@web/core/utils/functions";
import { renderToElement } from "@web/core/utils/render";

/**
 * @typedef { Object } EmbeddedComponentShared
 * @property { EmbeddedComponentPlugin['renderBlueprintToElement'] } renderBlueprintToElement
 */

/**
 * @typedef {((arg: { name, env, props }) => void)[]} on_will_mount_component_handlers
 * @typedef {(() => void)[]} on_component_mounted_handlers
 */

/**
 * This plugin is responsible with providing the API to manipulate/insert
 * sub components in an editor.
 */
export class EmbeddedComponentPlugin extends Plugin {
    static id = "embeddedComponents";
    static dependencies = ["history", "protectedNode", "selection"];
    static shared = ["renderBlueprintToElement"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        /** Handlers */
        on_attribute_changed_handlers: this.onChangeAttribute.bind(this),
        on_savepoint_restored_handlers: () => this.handleComponents(this.editable),
        on_history_reset_handlers: () => this.handleComponents(this.editable),
        on_history_reset_from_steps_handlers: () => this.handleComponents(this.editable),
        on_step_added_handlers: ({ stepCommonAncestor }) =>
            this.handleComponents(stepCommonAncestor),
        on_external_step_added_handlers: () => this.handleComponents(this.editable),

        /** Processors */
        clean_for_save_processors: (root) => this.cleanForSave(root),
        normalize_processors: withSequence(0, this.normalize.bind(this)),
        before_sanitize_processors: this.preProcessSanitizedElem.bind(this),
        after_sanitize_processors: this.postProcessSanitizedElem.bind(this),
        serializable_descendants_processors: this.processDescendantsToSerialize.bind(this),
        attribute_change_processors: this.onChangeAttribute.bind(this),

        /** Predicates */
        is_mutation_record_savable_predicates: this.isMutationRecordSavable.bind(this),

        /** Selectors */
        move_node_whitelist_selectors: "[data-embedded]",
    };

    setup() {
        this.components = new Set();
        // map from node to component info
        this.nodeMap = new WeakMap();
        this.app = this.config.embeddedComponentInfo.app;
        this.env = this.config.embeddedComponentInfo.env ?? {};
        this.hostToStateChangeManagerMap = new WeakMap();
        this.hostToOnComponentInsertedMap = new WeakMap();
        this.embeddedComponents = memoize((embeddedComponents = []) => {
            const result = {};
            for (const embedding of embeddedComponents) {
                // TODO ABD: Any embedding with the same name as another will overwrite it.
                // File currently relies on this system. Change it ?
                result[embedding.name] = embedding;
            }
            return result;
        });
        // First mount is done during on_history_reset_handlers which happens
        // when on_editor_started_handlers are called.
    }

    isMutationRecordSavable(record) {
        if (
            this.nodeMap.get(record.target) &&
            record.type === "attributes" &&
            record.attributeName === "data-embedded-props"
        ) {
            // This attribute is determined independently for each user
            // through `data-embedded-state` attribute mutations.
            return false;
        }
    }

    /**
     * @typedef {import("@html_editor/core/history_plugin").Tree} Tree
     *
     * @param {Tree[]} serializableDescendants
     * @param {Node} elem
     * @returns {Tree[]}
     */
    processDescendantsToSerialize(serializableDescendants, elem) {
        const embedding = this.getEmbedding(elem);
        if (!embedding) {
            return serializableDescendants;
        }
        return Object.values(embedding.getEditableDescendants?.(elem) || {}).map(nodeToTree);
    }

    handleComponents(elem) {
        this.destroyRemovedComponents([...this.components]);
        this.forEachEmbeddedComponentHost(elem, (host, embedding) => {
            const info = this.nodeMap.get(host);
            if (!info) {
                this.mountComponent(host, embedding);
            }
        });
    }

    forEachEmbeddedComponentHost(elem, callback) {
        const selector = `[data-embedded]`;
        const targets = [...elem.querySelectorAll(selector)];
        if (elem.matches(selector)) {
            targets.unshift(elem);
        }
        for (const host of targets) {
            const embedding = this.getEmbedding(host);
            if (!embedding) {
                continue;
            }
            callback(host, embedding);
        }
    }

    getEmbedding(host) {
        return this.embeddedComponents(this.getResource("embedded_components"))[
            host.dataset.embedded
        ];
    }

    /**
     * Apply an embedded state change received from `data-embedded-state`
     * attribute. In some cases (undo/redo/revertStepsUntil history operations),
     * the attribute has to be set to a new value, computed by the
     * stateChangeManager.
     *
     * @param {Object} attributeChange @see HistoryPlugin
     * @param { Object } options
     * @param { boolean } options.forNewStep whether the mutation is being used
     *        to create a new step
     * @returns {string} new attribute value to set on the node, which might be
     *        unchanged
     */
    onChangeAttribute(attributeChange, { forNewStep = false } = {}) {
        const attributeValue = attributeChange.value;
        let newAttributeValue;
        if (attributeChange.attributeName === "data-embedded-state") {
            const attrState = attributeChange.reverse
                ? attributeChange.oldValue
                : attributeChange.value;
            const stateChangeManager = this.getStateChangeManager(attributeChange.target);
            if (stateChangeManager) {
                // onStateChanged returns undefined if no change is needed for
                // the attribute value
                newAttributeValue = stateChangeManager.onStateChanged(attrState, {
                    reverse: attributeChange.reverse,
                    forNewStep,
                });
            }
        }
        attributeChange.value = newAttributeValue || attributeValue;
        return attributeChange;
    }

    getStateChangeManager(host) {
        const embedding = this.getEmbedding(host);
        if (!("getStateChangeManager" in embedding)) {
            return null;
        }
        if (!this.hostToStateChangeManagerMap.has(host)) {
            const config = {
                host,
                commitStateChanges: () => this.dependencies.history.addStep(),
            };
            const stateChangeManager = embedding.getStateChangeManager(config);
            stateChangeManager.setup();
            this.hostToStateChangeManagerMap.set(host, stateChangeManager);
        }
        return this.hostToStateChangeManagerMap.get(host);
    }

    mountComponent(
        host,
        { Component, getEditableDescendants, getProps, name, getStateChangeManager }
    ) {
        const props = getProps?.(host) || {};
        const env = Object.create(this.env);
        env.editorShared = {};
        if (getStateChangeManager) {
            env.getStateChangeManager = this.getStateChangeManager.bind(this);
        }
        if (getEditableDescendants) {
            env.getEditableDescendants = getEditableDescendants;
            // Enable the automatic selection restoration feature in @see useEditableDescendants
            Object.assign(env.editorShared, {
                selection: { ...this.dependencies.selection },
            });
        }
        this.trigger("on_will_mount_component_handlers", { name, env, props });
        const root = this.app.createRoot(Component, {
            props,
            env,
        });
        root.mount(host);
        // Patch mount fiber to hook into the exact call stack where root is
        // mounted (but before). This will remove host children synchronously
        // just before adding the root rendered html.
        const fiber = root.node.fiber;
        const fiberComplete = fiber.complete;
        fiber.complete = () => {
            host.replaceChildren();
            fiberComplete.call(fiber);
            this.trigger("on_component_mounted_handlers");
        };
        const onComponentInserted = this.extractOnComponentInserted(host);
        if (onComponentInserted) {
            // If a pending operation should be executed after the first mount
            // of an inserted blueprint, add it as the last `onMounted` callback
            root.node.mounted.push(onComponentInserted);
        }
        const info = {
            root,
            host,
        };
        this.components.add(info);
        this.nodeMap.set(host, info);
    }

    destroyRemovedComponents(infos) {
        // Avoid registering mutations if removed hosts are handled in
        // the same microtask as when they were removed.
        this.dependencies.history.ignoreDOMMutations(() => {
            for (const info of infos) {
                if (!this.editable.contains(info.host)) {
                    const host = info.host;
                    const display = host.style.display;
                    const parentNode = host.parentNode;
                    const clone = host.cloneNode(false);
                    if (parentNode) {
                        parentNode.replaceChild(clone, host);
                    }
                    host.style.display = "none";
                    this.editable.after(host);
                    this.destroyComponent(info);
                    if (parentNode) {
                        parentNode.replaceChild(host, clone);
                    } else {
                        host.remove();
                    }
                    host.style.display = display;
                    if (!host.getAttribute("style")) {
                        host.removeAttribute("style");
                    }
                }
            }
        });
    }

    deepDestroyComponent({ host }) {
        const removed = [];
        this.forEachEmbeddedComponentHost(host, (containedHost) => {
            const info = this.nodeMap.get(containedHost);
            if (info) {
                if (this.editable.contains(containedHost)) {
                    this.destroyComponent(info);
                } else {
                    removed.push(info);
                }
            }
        });
        this.destroyRemovedComponents(removed);
    }

    /**
     * Should not be called directly as it will not handle recursivity and
     * removed components @see deepDestroyComponent
     */
    destroyComponent({ root, host }) {
        const { getEditableDescendants } = this.getEmbedding(host);
        const editableDescendants = getEditableDescendants?.(host) || {};
        root.destroy();
        this.components.delete(arguments[0]);
        this.nodeMap.delete(host);
        host.append(...Object.values(editableDescendants));
    }

    destroy() {
        super.destroy();
        for (const info of [...this.components]) {
            if (this.components.has(info)) {
                this.deepDestroyComponent(info);
            }
        }
    }

    /**
     * @param {String} template blueprint for the embedded Component
     * @param {Object} [context] rendering context
     * @param {Function} [onComponentInserted] function to be executed when
     *        it is first mounted after it was inserted in the DOM. It will not
     *        be executed if the blueprint is removed from the DOM before the
     *        first mount nor if the component is mounted again afterwards.
     * @returns {HTMLElement} host
     */
    renderBlueprintToElement(template, context = {}, onComponentInserted = undefined) {
        const host = renderToElement(template, context);
        if (onComponentInserted) {
            this.hostToOnComponentInsertedMap.set(host, onComponentInserted);
        }
        return host;
    }

    extractOnComponentInserted(host) {
        const onComponentInserted = this.hostToOnComponentInsertedMap.get(host);
        this.hostToOnComponentInsertedMap.delete(host);
        return onComponentInserted;
    }

    normalize(elem) {
        this.forEachEmbeddedComponentHost(elem, (host, { getEditableDescendants }) => {
            this.dependencies.protectedNode.setProtectingNode(host, true);
            const editableDescendants = getEditableDescendants?.(host) || {};
            for (const editableDescendant of Object.values(editableDescendants)) {
                this.dependencies.protectedNode.setProtectingNode(editableDescendant, false);
            }
        });
    }

    cleanForSave(clone) {
        this.forEachEmbeddedComponentHost(clone, (host, { getEditableDescendants }) => {
            // In this case, host is a cloned element, there is no OWL root
            // attached to it.
            const editableDescendants = getEditableDescendants?.(host) || {};
            host.replaceChildren();
            for (const editableDescendant of Object.values(editableDescendants)) {
                delete editableDescendant.dataset.oeProtected;
                host.append(editableDescendant);
            }
            delete host.dataset.oeProtected;
            delete host.dataset.embeddedState;
        });
    }

    preProcessSanitizedElem(elem) {
        if (elem?.nodeType !== Node.ELEMENT_NODE) {
            return elem;
        }
        for (const host of selectElements(elem, "[data-embedded-props], [data-embedded-state]")) {
            if (host.dataset.embeddedProps) {
                host.dataset.embeddedProps = encodeURIComponent(host.dataset.embeddedProps);
            }
            if (host.dataset.embeddedState) {
                host.dataset.embeddedState = encodeURIComponent(host.dataset.embeddedState);
            }
        }
        return elem;
    }

    postProcessSanitizedElem(elem) {
        if (elem?.nodeType !== Node.ELEMENT_NODE) {
            return elem;
        }
        for (const host of selectElements(elem, "[data-embedded-props], [data-embedded-state]")) {
            if (host.dataset.embeddedProps) {
                host.dataset.embeddedProps = decodeURIComponent(host.dataset.embeddedProps);
            }
            if (host.dataset.embeddedState) {
                host.dataset.embeddedState = decodeURIComponent(host.dataset.embeddedState);
            }
        }
        return elem;
    }
}
