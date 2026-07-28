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
 * @typedef { import("../core/dom_reference_map_plugin").NodeId } NodeId
 * @typedef { import("../core/history_plugin").HistoryCommitData } HistoryCommitData
 */

/**
 * @typedef { Object } StateChange
 * @property { NodeId } nodeId
 * @property { Object } previous
 * @property { Object } next
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
        history_commit_data_properties: ["embeddedStateChanges"],

        /** Handlers */
        on_savepoint_restored_handlers: (savePoint) => {
            /** @type { StateChange[] } */
            const changes = savePoint.data.embeddedStateChanges;
            if (changes?.length) {
                this.applyStateChanges(changes);
                this.pendingStateChanges.push(...changes);
            }
            this.handleComponents(this.editable);
        },
        on_will_reset_history_handlers: this.resetPendingStateChanges.bind(this),
        on_history_reset_handlers: () => this.handleComponents(this.editable),
        on_history_rebased_handlers: () => this.handleComponents(this.editable),
        on_committed_to_history_handlers: (commit) => {
            const root =
                this.dependencies.domObserver.getMutationsCommonAncestor(
                    commit.data.mutations || []
                ) || this.editable;
            this.handleComponents(root);
            this.resetPendingStateChanges();
        },
        on_apply_history_commit_handlers: (commit) => {
            /** @type { StateChange[] } */
            const changes = commit.data.embeddedStateChanges;
            if (changes?.length) {
                this.applyStateChanges(changes);
            }
        },
        on_revert_history_commit_handlers: (commit) => {
            /** @type { StateChange[] } */
            const changes = commit.data.embeddedStateChanges;
            if (changes?.length) {
                this.applyStateChanges(changes, { reverse: true });
            }
        },
        on_will_invalidate_pending_changes_handlers: () => {
            /** @type { StateChange[] } */
            const changes = [...this.pendingStateChanges];
            this.resetPendingStateChanges();
            this.applyStateChanges(changes, { reverse: true });
        },
        on_pending_changes_unstashed_handlers: (stashedCommit) => {
            /** @type { StateChange[] } */
            const changes = stashedCommit.data.embeddedStateChanges;
            if (changes?.length) {
                this.pendingStateChanges.push(...changes);
            }
        },
        on_will_capture_history_changes_handlers: () => {
            this.isCapturingHistoryChanges = true;
        },
        on_history_changes_captured_handlers: () => {
            this.isCapturingHistoryChanges = false;
        },

        /** Processors */
        clean_for_save_processors: (root) => this.cleanForSave(root),
        normalize_processors: withSequence(0, this.normalize.bind(this)),
        before_sanitize_processors: this.preProcessSanitizedElem.bind(this),
        after_sanitize_processors: this.postProcessSanitizedElem.bind(this),
        serializable_descendants_processors: this.processDescendantsToSerialize.bind(this),
        pending_history_commit_data_processors: this.processCommitData.bind(this),
        save_point_history_commit_data_processors: this.processCommitData.bind(this),

        /** Predicates */
        is_mutation_savable_predicates: this.isMutationSavable.bind(this),
        has_history_commit_changes_predicates: (commit) => {
            if (commit.data.embeddedStateChanges?.length) {
                return true;
            }
        },

        /** Selectors */
        move_node_whitelist_selectors: "[data-embedded]",
    };

    setup() {
        this.resetPendingStateChanges();
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

    resetPendingStateChanges() {
        /** @type {StateChange[]} */
        this.pendingStateChanges = [];
    }

    /**
     * Add the currently pending state changes to the given commit data and
     * return it.
     *
     * @param {HistoryCommitData} data
     * @returns {HistoryCommitData & {embeddedStateChanges: StateChange[]}}
     */
    processCommitData(data) {
        return {
            ...data,
            embeddedStateChanges: [...this.pendingStateChanges],
        };
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
            // through `embeddedStateChanges`.
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

    getStateChangeManager(host) {
        const embedding = this.getEmbedding(host);
        if (!("getStateChangeManager" in embedding)) {
            return null;
        }
        if (!this.hostToStateChangeManagerMap.has(host)) {
            const config = {
                host,
                stageStateChange: (previous, next) => {
                    this.pendingStateChanges.push({
                        nodeId: this.dependencies.domReferenceMap.getNodeId(host),
                        previous,
                        next,
                    });
                },
                commitStateChanges: () => this.dependencies.history.commit(),
            };
            const stateChangeManager = embedding.getStateChangeManager(config);
            stateChangeManager.setup();
            this.hostToStateChangeManagerMap.set(host, stateChangeManager);
        }
        return this.hostToStateChangeManagerMap.get(host);
    }

    /**
     * Apply (or revert if `reverse` is true) the given state changes.
     *
     * @param {StateChange[]} changes
     * @param {Object} [options = {}]
     * @param {boolean} [reverse = false]
     */
    applyStateChanges(changes, { reverse = false } = {}) {
        for (const { nodeId, previous, next } of changes) {
            const host = this.dependencies.domReferenceMap.getNodeById(nodeId);
            const manager = host && this.getStateChangeManager(host);
            if (manager) {
                const { before, after } = manager.applyStateChange(
                    reverse ? next : previous,
                    reverse ? previous : next
                );
                const hasStateChanged = JSON.stringify(before) !== JSON.stringify(after);
                if (this.isCapturingHistoryChanges && hasStateChanged) {
                    this.pendingStateChanges.push({ nodeId, previous: before, next: after });
                }
            }
        }
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
        // If a pending operation should be executed after the first mount of
        // an inserted blueprint, run it synchronously right after the mounted
        // callbacks, in the same call stack as the DOM insertion.
        const onComponentInserted = this.extractOnComponentInserted(host);
        const { root } = mountComponent(this.app, Component, host, props, env, {
            onAfterComplete: () => {
                onComponentInserted?.();
                this.trigger("on_component_mounted_handlers");
            },
        });
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
        return elem;
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
        });
        return clone;
    }

    preProcessSanitizedElem(elem) {
        if (elem?.nodeType !== Node.ELEMENT_NODE) {
            return elem;
        }
        for (const host of selectElements(elem, "[data-embedded-props]")) {
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
        for (const host of selectElements(elem, "[data-embedded-props]")) {
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
