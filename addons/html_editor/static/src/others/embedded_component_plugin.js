import { nodeToTree } from "@html_editor/core/dom_reference_map_plugin";
import { mountComponent } from "@html_editor/others/embedded_component_utils";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { selectElements } from "@html_editor/utils/dom_traversal";
import { memoize } from "@web/core/utils/functions";
import { renderToElement } from "@web/core/utils/render";
import { NATIVE_MUTATION_TYPES } from "@html_editor/core/dom_observer_plugin";

/**
 * @typedef { Object } EmbeddedComponentShared
 * @property { EmbeddedComponentPlugin['renderBlueprintToElement'] } renderBlueprintToElement
 */

/**
 * @typedef { import("@html_editor/core/dom_observer_plugin").SerializedMutation<"attributes"> } SerializedAttributesMutation
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
    static dependencies = [
        "history",
        "domObserver",
        "domReferenceMap",
        "protectedNode",
        "selection",
    ];
    static shared = ["renderBlueprintToElement"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        /** Handlers */
        on_savepoint_restored_handlers: () => this.handleComponents(this.editable),
        on_history_reset_handlers: () => this.handleComponents(this.editable),
        on_history_rebased_handlers: () => this.handleComponents(this.editable),
        on_committed_to_history_handlers: (commit) => {
            const root =
                this.dependencies.domObserver.getMutationsCommonAncestor(
                    commit.data.mutations || []
                ) || this.editable;
            this.handleComponents(root);
        },

        /** Processors */
        clean_for_save_processors: (root) => this.cleanForSave(root),
        normalize_processors: withSequence(0, this.normalize.bind(this)),
        before_sanitize_processors: this.preProcessSanitizedElem.bind(this),
        after_sanitize_processors: this.postProcessSanitizedElem.bind(this),
        serializable_descendants_processors: this.processDescendantsToSerialize.bind(this),
        attributes_mutation_value_processors: this.processAttributesMutationValue.bind(this),

        /** Predicates */
        is_mutation_savable_predicates: this.isMutationSavable.bind(this),

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
        // First mount is done during on_will_reset_history_handlers which happens
        // when on_editor_started_handlers are called.
    }

    /**
     * @param {import("@html_editor/core/dom_observer_plugin").NativeMutation} mutation
     * @returns {boolean | undefined}
     */
    isMutationSavable(mutation) {
        if (
            this.nodeMap.get(mutation.target) &&
            mutation.type === NATIVE_MUTATION_TYPES.ATTRIBUTES &&
            mutation.attributeName === "data-embedded-props"
        ) {
            // This attribute is determined independently for each user
            // through `data-embedded-state` attribute mutations.
            return false;
        }
    }

    /**
     * @typedef {import("@html_editor/core/dom_reference_map_plugin").Tree} Tree
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
     * attribute. In some cases (undo/redo/revertCommitsUntil history operations),
     * the attribute has to be set to a new value, computed by the
     * stateChangeManager.
     *
     * @param { string } value
     * @param { Object } options
     * @param { SerializedAttributesMutation } options.mutation
     * @param { boolean } [options.ensureNewMutations = false] whether the mutation is being used
     *        to create a new commit and requires to ensure new mutations are generated
     * @param { boolean } [options.wasReversed = false] whether the change was reversed
     * @returns {string} new attribute value to set on the node, which might be unchanged
     */
    processAttributesMutationValue(
        value,
        { mutation, ensureNewMutations = false, wasReversed = false }
    ) {
        if (mutation.attributeName === "data-embedded-state") {
            const attrState = wasReversed ? mutation.oldValue : value;
            const target = this.dependencies.domReferenceMap.getNodeById(mutation.nodeId);
            // onStateChanged returns undefined if no change is needed for
            // the attribute value
            return (
                this.getStateChangeManager(target)?.onStateChanged(attrState, {
                    reverse: wasReversed,
                    ensureNewMutations,
                }) ?? value
            );
        } else {
            return value;
        }
    }

    getStateChangeManager(host) {
        const embedding = this.getEmbedding(host);
        if (!("getStateChangeManager" in embedding)) {
            return null;
        }
        if (!this.hostToStateChangeManagerMap.has(host)) {
            const config = {
                host,
                commitStateChanges: () => this.dependencies.history.commit(),
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
        const { root } = mountComponent(this.app, Component, host, props, env, {
            onAfterComplete: () => this.trigger("on_component_mounted_handlers"),
        });
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
        this.dependencies.domObserver.ignore(() => {
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
