import { Plugin } from "../plugin";
import { trackOccurrences, trackOccurrencesPair } from "@html_editor/utils/tracking";
import { treeToNodes, nodeToTree } from "./dom_reference_map_plugin";
import { childNodes, getCommonAncestor } from "@html_editor/utils/dom_traversal";
import { omit, pick } from "@web/core/utils/objects";
import { toggleClass } from "@html_editor/utils/dom";
import { withSequence } from "@html_editor/utils/resource";

/**
 * @type { MutationObserverInit }
 */
const OBSERVER_OPTIONS = {
    childList: true,
    subtree: true,
    attributes: true,
    attributeOldValue: true,
    characterData: true,
    characterDataOldValue: true,
};

export const NATIVE_MUTATION_TYPES = /** @type {const} */ ({
    ATTRIBUTES: "attributes",
    CHARACTER_DATA: "characterData",
    CHILD_LIST: "childList",
});
export const EDITOR_MUTATION_TYPES = /** @type {const} */ ({
    ATTRIBUTES: "attributes",
    CHARACTER_DATA: "characterData",
    CLASS_LIST: "classList",
    ADD: "add",
    REMOVE: "remove",
    CUSTOM: "custom",
});

/**
 * @typedef { typeof NATIVE_MUTATION_TYPES[keyof typeof NATIVE_MUTATION_TYPES] } NativeMutationType
 * @typedef { typeof EDITOR_MUTATION_TYPES[keyof typeof EDITOR_MUTATION_TYPES] } EditorMutationType
 */

/**
 * Native Mutations
 * ----------------
 *
 * Narrowed typing for the native `MutationRecord` type, to differentiate between
 * each mutation type, omitting all properties that are always `null` for the
 * given type of mutation.
 *
 * @template { NativeMutationType } [T=NativeMutationType]
 * @typedef { Extract<|
 *    (Pick<MutationRecord, "target" | "attributeName" | "attributeNamespace" | "oldValue"> & { type: "attributes" })
 *  | (Pick<MutationRecord, "target" | "oldValue"> & { type: "characterData" })
 *  | (Pick<MutationRecord, "target" | "addedNodes" | "removedNodes" | "previousSibling" | "nextSibling"> & { type: "childList" }),
 * { type: T }
 * > } NativeMutation
 */

/** @typedef { import("./dom_reference_map_plugin").Tree } Tree */

/**
 * Editor Mutations
 * ----------------
 *
 * Expanded mutation object, with extra information that is helpful for our
 * purposes in the editor.
 *
 * @template { EditorMutationType } [T=EditorMutationType]
 * @typedef { Extract<|
 *    (NativeMutation<"attributes"> | { value: string })
 *  | (Omit<NativeMutation<"attributes">, "attributeName" | "attributeNamespace" | "type"> & { type: "classList", className: string, value: boolean })
 *  | (NativeMutation<"characterData"> | { value: string })
 *  | (Pick<NativeMutation<"childList">, "previousSibling" | "nextSibling"> | { tree: Tree, parent: Node } & { type: "add" })
 *  | (Pick<NativeMutation<"childList">, "previousSibling" | "nextSibling"> | { tree: Tree, parent: Node } & { type: "remove" })
 *  | { apply: Function, revert: Function } & { type: "custom" },
 * { type: T }
 * > } EditorMutation
 */

/** @typedef { import("./dom_reference_map_plugin").NodeId } NodeId */
/** @typedef { import("./dom_reference_map_plugin").SerializedNode } SerializedNode */

/**
 * Serialized Mutations
 * --------------------
 *
 * Serialized version of `EditorMutation`s for safely passing around the editor
 * without losing references and to allow as JSON payload.
 *
 * @template { EditorMutationType } [T=EditorMutationType]
 * @typedef { Extract<|
 *     (Omit<EditorMutation<"attributes">, "target"> & { nodeId: NodeId })
 *   | (Omit<EditorMutation<"classList">, "target"> & { nodeId: NodeId })
 *   | (Omit<EditorMutation<"characterData">, "target"> & { nodeId: NodeId })
 *   | (Omit<EditorMutation<"classList">, "target"> & { nodeId: NodeId })
 *   | (Omit<EditorMutation<"add">, "target" | "previousSibling" | "nextSibling" | "tree" | "parent"> & { nodeId: NodeId, previousNodeId: NodeId, nextNodeId: NodeId, serializedNode: SerializedNode, parentNodeId: NodeId })
 *   | (Omit<EditorMutation<"remove">, "target" | "previousSibling" | "nextSibling" | "tree" | "parent"> & { nodeId: NodeId, previousNodeId: NodeId, nextNodeId: NodeId, serializedNode: SerializedNode, parentNodeId: NodeId }),
 *   { type: T }
 * > } SerializedMutation
 */

/** @typedef { WeakMap<NativeMutation<"childList">, { added: Tree[], removed: Tree[] }> } ChildListToTreesMap */

/**
 * @typedef { Object } DomObserverShared
 * @property { DomObserverPlugin['ignore'] } ignore
 * @property { DomObserverPlugin['hasStagedMutations'] } hasStagedMutations
 * @property { DomObserverPlugin['stageCustomMutation'] } stageCustomMutation
 * @property { DomObserverPlugin['applyCustomMutation'] } applyCustomMutation
 * @property { DomObserverPlugin['getMutationsCommonAncestor'] } getMutationsCommonAncestor
 * @property { DomObserverPlugin['getClassChanges'] } getClassChanges
 */

/**
 * @typedef { ((root: HTMLElement) => void)[] } on_content_updated_handlers
 * @typedef { (() => void)[] } on_pending_mutations_normalized_handlers
 * @typedef { ((mutations: SerializedMutation[]) => void)[] } on_pending_mutations_staged_handlers
 * @typedef { ((mutations: NativeMutation[]) => void)[] } on_will_filter_mutations_handlers
 *
 * @typedef { ((node: Node, attributeName: string, attributeValue: string) => boolean)[] } set_attribute_overrides
 *
 * @typedef { ((value: string, params: { mutation: NativeMutation<"attributes">, ensureMutations?: boolean, wasReversed?: boolean }) => string)[] } attributes_mutation_value_processors
 *
 * @typedef { ((mutation: NativeMutation) => boolean | undefined)[] } is_mutation_savable_predicates
 * @typedef { ((mutation: EditorMutation<"classList">) => boolean | undefined)[] } is_classlist_mutation_savable_predicates
 */

export class DomObserverPlugin extends Plugin {
    static id = "domObserver";
    static dependencies = ["domReferenceMap"];
    static shared = [
        "ignore",
        "hasStagedMutations",
        "stageCustomMutation",
        "applyCustomMutation",
        "getMutationsCommonAncestor",
        "getClassChanges",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        history_commit_data_properties: ["mutations"],

        // Handlers
        // --------

        // Start / Refresh
        on_editor_started_handlers: withSequence(9, this.observe.bind(this)),
        on_will_reset_history_handlers: this.reset.bind(this),
        on_committed_to_history_handlers: () => {
            this.triggerContentUpdated();
            this.clearStage();
        },

        // Remote / Rebase
        on_will_rebase_history_handlers: () => {
            /** Applying remote changes to the history (resetting from commits
            or adding a remote commit) shouldn't produce new mutations or
            affect the `oldValue` state. We will restore the observer
            afterwards, via { @see on_history_rebased_handlers }. */
            this.disconnect();
        },
        on_history_rebased_handlers: () => {
            /** @see on_will_rebase_history_handlers */
            this.observe();
        },
        on_remote_history_commit_applied_handlers: (newCommit) => {
            const root =
                this.getMutationsCommonAncestor(newCommit.data.mutations || []) || this.editable;
            this.processThrough("normalize_processors", root);
        },

        // Apply / Revert
        on_apply_history_commit_handlers: (commit, { ensureNewMutations = false } = {}) => {
            if (commit.data.mutations) {
                this.applyMutations(commit.data.mutations, { ensureNewMutations });
            }
        },
        on_revert_history_commit_handlers: (commit, { ensureNewMutations = false } = {}) => {
            if (commit.data.mutations) {
                this.revertMutations(commit.data.mutations, { ensureNewMutations });
            }
        },
        on_will_invalidate_pending_changes_handlers: () => this.discardPendingMutations(),

        // Preview
        on_history_commit_restored_handlers: () => {
            // Process and stage mutations so that the attribute comparison for
            // the state change is done with the intermediate attribute value
            // and not with the final value in the DOM after all commits were
            // reverted then applied again.
            this.flush();
        },
        on_irreversible_history_commit_applied_handlers: () => {
            this.flush();
        },
        on_savepoint_restored_handlers: withSequence(0, (savePoint) => {
            // Apply draft mutations to recover the same mutations state as before.
            this.applyMutations(savePoint.data.mutations, { ensureNewMutations: true });
            this.stagePendingMutations();
            this.triggerContentUpdated();
        }),
        on_pending_changes_unstashed_handlers: (stashedCommit) => {
            if (stashedCommit.data.mutations && !this.isObserving) {
                // Make sure the unstashed mutations are recorded.
                this.stage(stashedCommit.data.mutations);
            }
        },
        on_prepare_drag_handlers: this.disableHasStagedMutationsWarning.bind(this),

        // Processors
        // ----------

        pending_history_commit_data_processors: withSequence(0, (data) =>
            this.processPendingData(data)
        ),
        snapshot_history_commit_data_processors: (data) => {
            data.mutations = childNodes(this.editable)
                .filter((node) => this.dependencies.domReferenceMap.hasNode(node))
                .map((node) => ({
                    type: EDITOR_MUTATION_TYPES.ADD,
                    parentNodeId: "root",
                    nodeId: this.dependencies.domReferenceMap.getNodeId(node),
                    serializedNode: this.dependencies.domReferenceMap.serializeTree(
                        nodeToTree(node)
                    ),
                    nextNodeId: null,
                }));
            return data;
        },
        save_point_history_commit_data_processors: (data) => {
            this.stagePendingMutations();
            return { ...data, mutations: [...this.mutations] };
        },

        // Predicates
        // ----------

        has_history_commit_changes_predicates: (commit) => {
            if ("mutations" in commit.data) {
                return !!commit.data.mutations.length;
            }
        },
    };

    setup() {
        this.mutationFilteredClasses = new Set(this.getResource("system_classes"));
        this.mutationFilteredAttributes = new Set(this.getResource("system_attributes"));
        this.observer = new MutationObserver((mutations) => this.stagePendingMutations(mutations));
        this.ignoreMutationsIds = new Set();
        this._cleanups.push(() => {
            this.observer.disconnect();
            this.isObserverConnected = false;
        });
        this.reset();
    }

    /**
     * Reset the staged mutations and the `oldValue` manager.
     */
    reset() {
        this.clearStage();
        if (this.oldValueManager) {
            this.oldValueManager.reset();
        } else {
            this.oldValueManager = new OldValueManager();
        }
    }

    // ===================
    // Observer management
    // ===================

    /**
     * Start observing mutations.
     */
    observe() {
        this.observer.observe(this.editable, OBSERVER_OPTIONS);
        this.isObserverConnected = true;
    }

    /**
     * Disconnect the observer to stop observing mutations.
     */
    disconnect() {
        this.stagePendingMutations();
        this.observer.disconnect();
        this.isObserverConnected = false;
    }

    /**
     * Execute {@link callback} while ignore all DOM mutation without
     * disconnecting the observer so as to keep updating the `oldValueManager`'s
     * state) ({ @see processNativeMutations }).
     *
     * /!\ This method should be used with extreme caution. Not observing some
     * mutations could lead to mutations that are impossible to undo/redo.
     *
     * /!\ Do not re-introduce nodes that had been already added to the DOM in a
     * commit ({ @see isObservedNode }).
     *
     * @param { Function } callback
     */
    ignore(callback) {
        const ignoreId = Math.floor(Math.random() * Math.pow(2, 52)).toString();
        this.ignoreMutationsIds.add(ignoreId);
        this.stagePendingMutations();
        this.isIgnoring = true;
        try {
            return callback();
        } finally {
            this.ignoreMutationsIds.delete(ignoreId);
            if (!this.ignoreMutationsIds.size) {
                this.stagePendingMutations();
                this.isIgnoring = false;
            }
        }
    }

    /**
     * Is true if the observer is connected and active, false otherwise.
     */
    get isObserving() {
        return !!this.isObserverConnected && !this.isIgnoring;
    }

    /**
     * Any node that was added to the DOM without a mutation record in a commit
     * (typically due to {@link ignore}) is considered an unobserved node.
     *
     * A known limitation to this approach is when a node that had been present
     * in the editable before (and thus has an entry in the nodeMap) is re-added
     * with {@link ignore}. Such node will not be flagged as unobserved and
     * history might become inconsistent.
     *
     * @param { Node } node
     * @returns { boolean }
     */
    isObservedNode(node) {
        return this.dependencies.domReferenceMap.hasNode(node);
    }

    // =======
    // Staging
    // =======

    /**
     * Stage the given serialized mutation(s).
     *
     * @param { SerializedMutation | SerializedMutation[] } mutations
     */
    stage(mutations) {
        mutations = Array.isArray(mutations) ? mutations : [mutations];
        this.mutations.push(...mutations);
    }

    /**
     * Clears the stage of all mutations.
     */
    clearStage() {
        /** @type { SerializedMutation[] } */
        this.mutations = [];
    }

    /**
     * Process the given native mutation records (or take the observer's current
     * mutation records by default) and stage them, then notify plugins.
     *
     * Note: this is meant to handle new mutations from the observer. The only
     * reason it accepts mutations as argument is for the observer's callback to
     * be able to use it.
     *
     * @param { NativeMutation[] } [mutations = this.observer.takeRecords()]
     * @returns { SerializedMutation[] }
     */
    stagePendingMutations(mutations = this.observer.takeRecords()) {
        const serializedMutations = this.flush(mutations);
        if (serializedMutations.length) {
            // TODO modify `handleMutations` of web_studio to handle `undoOperation`.
            this.trigger("on_pending_mutations_staged_handlers", serializedMutations);
            // Process potential new mutations caused by the handlers.
            this.flush();
        }
        return serializedMutations;
    }

    /**
     * Process the given native mutation records (or take the observer's current
     * mutation records by default) and stage them. Will not notify plugins.
     *
     * Note: this is meant to handle new mutations from the observer. The only
     * reason it accepts mutations as argument is for the observer's callback to
     * be able to use it.
     *
     * @param { NativeMutation[] } [mutations = this.observer.takeRecords()]
     * @returns { SerializedMutation[] }
     */
    flush(mutations = this.observer.takeRecords()) {
        const processedMutations = this.processNativeMutations(mutations);
        const serializedMutations = this.serializeEditorMutations(processedMutations);
        this.stage(serializedMutations);
        return serializedMutations;
    }

    /**
     * Process and stage all pending mutations then include all staged mutations
     * into the provided `data` object before returning it.
     *
     * @typedef { import("./history_plugin").HistoryCommitData } HistoryCommitData
     * @param { HistoryCommitData } data
     * @returns { HistoryCommitData & { mutations: SerializedMutation[] } }
     */
    processPendingData(data) {
        const hasRelatedCommit = !!data.relatedCommit;
        // Stage the observer's current changes.
        if (hasRelatedCommit) {
            this.flush();
        } else {
            this.stagePendingMutations();
        }
        const currentMutationsCount = this.mutations.length;
        if (currentMutationsCount) {
            // Normalize the mutated nodes. Note: this can cause other commits
            // to be written.
            const commitRoot = this.getMutationsCommonAncestor(this.mutations) || this.editable;
            this.processThrough("normalize_processors", commitRoot);
            if (!hasRelatedCommit) {
                this.trigger("on_pending_mutations_normalized_handlers");
            }
            this.flush();
            if (currentMutationsCount === this.mutations.length) {
                // If there was no added staged mutation during the
                // normalization commit, force the trigger of a content_updated
                // to allow i.e. the hint plugin to react to non-observed
                // changes (i.e. a div becoming a baseContainer).
                this.triggerContentUpdated();
            }
        }
        return { ...data, mutations: [...this.mutations] };
    }

    /**
     * Process and revert all pending mutations.
     */
    discardPendingMutations() {
        this.flush();
        this.revertMutations([...this.mutations]);
        this.observer.takeRecords();
        this.clearStage();
    }

    /**
     * @deprecated Use special commit data and apply/revert resource subscribers
     * instead of this.
     *
     * @todo This mutation type definitely fails in collaborative since it's not
     * serializable. If we ever use it in a context that uses collaboration,
     * we'll need to adapt it.
     *
     * @param { Object } spec
     * @param { Function } spec.apply
     * @param { Function } spec.revert
     */
    stageCustomMutation({ apply, revert }) {
        /** @type { EditorMutation<"custom"> } */
        const customMutation = {
            type: EDITOR_MUTATION_TYPES.CUSTOM,
            apply: () => {
                apply();
                this.stageCustomMutation({ apply, revert });
            },
            revert: () => {
                revert();
                this.stageCustomMutation({ apply: revert, revert: apply });
            },
        };
        this.stage(customMutation);
    }

    /**
     * Disable the warning in @see hasStagedMutations and return a function that
     * re-enables it.
     *
     * @returns { () => void }
     */
    disableHasStagedMutationsWarning() {
        this.ignoreHasStagedMutations = true;
        return () => {
            this.ignoreHasStagedMutations = false;
        };
    }

    /**
     * Return true if the staged changes include mutations of types
     * `characterData`, `remove` or `add`, false otherwise.
     *
     * @returns { boolean }
     */
    hasStagedMutations() {
        if (this.ignoreHasStagedMutations) {
            return false;
        }
        return !!this.mutations.find((m) =>
            [
                EDITOR_MUTATION_TYPES.CHARACTER_DATA,
                EDITOR_MUTATION_TYPES.ADD,
                EDITOR_MUTATION_TYPES.REMOVE,
            ].includes(m.type)
        );
    }

    // ===================
    // Mutation processing
    // ===================

    /**
     * Filter through a batch of `NativeMutation`s then turn them into
     * `EditorMutation`s by adding information to them and splitting them so we
     * have individual records for each class change, each added node and each
     * removed nodes, and assign an ID to any added node.
     *
     * @param { NativeMutation[] } mutations
     * @returns { EditorMutation[] }
     */
    processNativeMutations(mutations) {
        this.trigger("on_will_filter_mutations_handlers", mutations);

        // Filter out same-textContent mutations. This needs to happen
        // first because it could affect the siblings computations below.
        mutations = mutations.filter((mutation) => {
            if (mutation.type === NATIVE_MUTATION_TYPES.CHILD_LIST) {
                // Check if a mutation consists of removing and adding a single
                // text node with the same text content, which occurs in Firefox
                // but is optimized away in Chrome.
                const { addedNodes, removedNodes } = mutation;
                const [firstAdded, firstRemoved] = [addedNodes[0], removedNodes[0]];
                if (
                    [addedNodes, removedNodes].every((nodes) => nodes.length === 1) &&
                    [firstAdded, firstRemoved].every((node) => node.nodeType === Node.TEXT_NODE) &&
                    firstAdded.textContent === firstRemoved.textContent
                ) {
                    const oldId = this.dependencies.domReferenceMap.getNodeId(firstRemoved);
                    if (oldId) {
                        this.dependencies.domReferenceMap.set(firstAdded, oldId);
                        return false;
                    }
                }
            }
            return true;
        });

        // Build a map of childList trees for all the mutations.
        const childListToTrees = this.createChildListToTreesMap(mutations);

        // Track the attributes/characterData mutation occurrences.
        const [isFirstAttribute, isFirstCharData] = [trackOccurrencesPair(), trackOccurrences()];
        /**
         * @param { NativeMutation<"attributes" | "characterData"> } mutation
         * @returns { boolean }
         */
        const isFirstOccurrence = (mutation) =>
            mutation.type === NATIVE_MUTATION_TYPES.ATTRIBUTES
                ? isFirstAttribute(mutation.target, mutation.attributeName)
                : isFirstCharData(mutation.target);

        // Now do the processing.
        return mutations
            .flatMap((mutation) => {
                if (!this.isObservedNode(mutation.target)) {
                    return false;
                }
                const isSavable =
                    this.isObserving &&
                    (this.checkPredicates("is_mutation_savable_predicates", mutation) ?? true);
                switch (mutation.type) {
                    case NATIVE_MUTATION_TYPES.ATTRIBUTES:
                    case NATIVE_MUTATION_TYPES.CHARACTER_DATA: {
                        if (isSavable) {
                            // Keep only the first mutation record for each
                            // (node, attribute) pair. Mutation records of type
                            // "attribute" and "characterData" provide the old
                            // value, but not the new value. When multiple
                            // mutations occur in the same batch for an
                            // element's attribute or characterData, we only
                            // know the final value of the accumulated changes,
                            // which is the DOM's current state. The oldValue
                            // provided by mutations after the first one are
                            // intermediate states that we do not care about.
                            // Discarding them allows us to store a single
                            // record representing the accumulated changes,
                            // instead of reconstructing the new value
                            // introduced by each mutation.
                            if (isFirstOccurrence(mutation)) {
                                if (mutation.type === NATIVE_MUTATION_TYPES.ATTRIBUTES) {
                                    return this.processAttributesMutation(mutation);
                                } else {
                                    return this.processCharacterDataMutation(mutation);
                                }
                            }
                        } else {
                            // If the observer is disabled, store the last
                            // observed state of the target's affected property
                            // (attribute/class/textContent) and drop the
                            // record.
                            if (mutation.attributeName === "class") {
                                // If the record is a change in a class attribute, first split it so
                                // we can handle the old value of each class individually.
                                for (const clMutation of this.createClassListMutations(mutation)) {
                                    this.oldValueManager.store(clMutation);
                                }
                            } else {
                                this.oldValueManager.store(mutation);
                            }
                        }
                        return false;
                    }
                    case NATIVE_MUTATION_TYPES.CHILD_LIST: {
                        return (
                            isSavable && this.processChildListMutation(mutation, childListToTrees)
                        );
                    }
                }
            })
            .filter(Boolean);
    }

    /**
     * Process a native mutation of type "attributes" by turning it into one or
     * several `EditorMutation`s, or returning `false` if it should be ignored.
     *
     * This involves:
     * - splitting a change on the "class" attribute into an array of mutations
     *   of type "classList" @see createClassListMutations
     * - giving it a `value` property
     * - updating its `oldValue` property @see oldValueManager.apply
     *
     * @param { NativeMutation<"attributes"> } mutation
     * @returns { |
     *        EditorMutation<"attributes">
     *      | EditorMutation<"classList">[]
     *      | false }
     */
    processAttributesMutation(mutation) {
        if (
            // Skip the attributes change on the dom.
            mutation.target === this.editable ||
            mutation.attributeName === "contenteditable" ||
            // Skip system mutations.
            this.mutationFilteredAttributes.has(mutation.attributeName)
        ) {
            return false;
        }
        if (mutation.attributeName === "class") {
            return (
                this.createClassListMutations(mutation)
                    .map(this.oldValueManager.apply.bind(this.oldValueManager))
                    // Filter out no-op.
                    .filter((classRecord) => classRecord.value !== classRecord.oldValue)
            );
        } else {
            const value = this.processThrough(
                "attributes_mutation_value_processors",
                mutation.target.getAttribute(mutation.attributeName),
                { mutation: this.serializeAttributesMutation(mutation) }
            );
            /** @type { EditorMutation<"attributes"> } */
            let processedMutation = {
                ...pick(mutation, "type", "target", "attributeName", "oldValue"),
                value,
            };
            processedMutation = this.oldValueManager.apply(processedMutation);
            if (processedMutation.value === processedMutation.oldValue) {
                // Filter out no-op.
                return false;
            }
            return processedMutation;
        }
    }

    /**
     * Process a native mutation of type "characterData" by turning it into one
     * an `EditorMutation`, or returning `false` if it should be ignored.
     *
     * This involves:
     * - giving it a `value` property
     * - updating its `oldValue` property @see oldValueManager.apply
     *
     * @param { NativeMutation<"characterData"> } mutation
     * @returns { EditorMutation<"characterData"> | false }
     */
    processCharacterDataMutation(mutation) {
        const processedMutation = this.oldValueManager.apply(
            /** @type { EditorMutation<"characterData"> } */ {
                ...pick(mutation, "type", "target", "oldValue"),
                value: mutation.target.textContent,
            }
        );
        // Filter out no-ops.
        return processedMutation.value === processedMutation.oldValue ? false : processedMutation;
    }

    /**
     * Process a native mutation of type "childList" by turning it into an array
     * of single-node `EditorMutation`s of types "add" and/or "remove", or
     * returning `false` if it should be ignored.
     *
     * This involves:
     * - assigning IDs to all added nodes
     * - splitting the record into one record per item in the `addedNodes` and
     *   `removedNodes` arrays
     * - giving each newly created record the native mutation's target as
     *   `parent` property
     * - giving each newly created record a `tree` property containing the tree
     *   of the record's corresponding `addedNodes` or `removedNodes` item.
     *
     * Note: Splitting the record requires having build a `ChildListToTreesMap`
     * with @see createChildListToTreesMap using all the records in the batch.
     *
     * @param { NativeMutation<"childList"> } mutation
     * @param { ChildListToTreesMap } childListToTrees
     * @returns { EditorMutation<"add" | "remove">[] | false }
     */
    processChildListMutation(mutation, childListToTrees) {
        if (!this.dependencies.domReferenceMap.hasNode(mutation.target)) {
            throw new Error("Unknown parent node");
        }

        const trees = childListToTrees.get(mutation);

        // Filter out unobserved nodes in the removed trees.
        const removeUnobservedNodes = (tree) =>
            this.isObservedNode(tree.node)
                ? {
                      node: tree.node,
                      children: tree.children.map(removeUnobservedNodes).filter(Boolean),
                  }
                : null;
        trees.removed = trees.removed.map(removeUnobservedNodes).filter(Boolean);
        childListToTrees.set(mutation, trees); // TODO: probably not necessary.

        // Invalidate sibling references to unobserved nodes
        const previousSibling =
            mutation.previousSibling === null || this.isObservedNode(mutation.previousSibling)
                ? mutation.previousSibling
                : undefined;
        const nextSibling =
            mutation.nextSibling === null || this.isObservedNode(mutation.nextSibling)
                ? mutation.nextSibling
                : undefined;

        if (
            // Filter out no-op
            (!trees.added.length && !trees.removed.length) ||
            // Filter out mutation without a valid position for node insertion
            (previousSibling === undefined && nextSibling === undefined)
        ) {
            return false;
        }

        // Assign ids to newly added childList nodes early so later records in
        // the same `MutationObserver` batch can resolve them (notably in
        // `isObservedNode`).
        trees.added
            .flatMap(treeToNodes)
            .filter((node) => !this.dependencies.domReferenceMap.hasNode(node))
            // TODO: see if we can get rid of this case of `register` with
            // `setDescendentsIds = false`. That would likely involve redefining
            // `isObservedNode` so it's not using `domReferenceMap` to mark
            // observed nodes.
            .forEach((node) => this.dependencies.domReferenceMap.register(node, false));

        // Split the mutation into single node mutations.
        return [
            ...trees.removed.map((tree, index) => ({
                type: EDITOR_MUTATION_TYPES.REMOVE,
                tree,
                parent: mutation.target,
                previousSibling,
                nextSibling: trees.removed[index + 1]?.node || nextSibling,
            })),
            ...trees.added.map((tree, index) => ({
                type: EDITOR_MUTATION_TYPES.ADD,
                tree,
                parent: mutation.target,
                previousSibling: trees.added[index - 1]?.node || previousSibling,
                nextSibling,
            })),
        ];
    }

    /**
     * Break down a single class attribute `NativeMutation` into individual
     * class addition/removal `EditorMutation`s for more precise history
     * tracking.
     *
     * @param { NativeMutation<"attributes"> } mutation
     * @returns { EditorMutation<"classList">[] }
     */
    createClassListMutations(mutation) {
        // oldValue can be nullish, or have extra spaces
        const { addedClasses, removedClasses } = this.getClassChanges(mutation);

        /**
         * @param { string } className
         * @param { boolean } isAdded
         * @returns { EditorMutation<"classList"> }
         */
        const createClassListMutation = (className, isAdded) => ({
            type: EDITOR_MUTATION_TYPES.CLASS_LIST,
            target: mutation.target,
            className,
            value: isAdded,
            oldValue: !isAdded,
        });
        // Generate records for each class change, skipping system mutations.
        return [
            ...[...addedClasses].map((cls) => createClassListMutation(cls, true)),
            ...[...removedClasses].map((cls) => createClassListMutation(cls, false)),
        ].filter(
            (clMutation) =>
                !this.mutationFilteredClasses.has(clMutation.className) &&
                (this.checkPredicates("is_classlist_mutation_savable_predicates", clMutation) ??
                    true)
        );
    }

    /**
     * Return an object with the added and removed classes in a (native)
     * mutation on a class attribute.
     *
     * @param { NativeMutation<"attributes"> } mutation
     * @returns { { addedClasses: Set<string>, removedClasses: Set<string> } }
     */
    getClassChanges(mutation) {
        if (
            mutation.type === NATIVE_MUTATION_TYPES.ATTRIBUTES &&
            mutation.attributeName === "class"
        ) {
            const removeSystemClasses = (cls) =>
                new Set(cls && [...cls].filter((c) => c && !this.mutationFilteredClasses.has(c)));
            const classesBefore = removeSystemClasses(mutation.oldValue?.split(" "));
            const classesAfter = removeSystemClasses(mutation.target.classList);
            return {
                addedClasses: classesAfter.difference(classesBefore),
                removedClasses: classesBefore.difference(classesAfter),
            };
        } else {
            return {};
        }
    }

    /**
     * `NativeMutation` records of type "childList" do not contain information
     * about the descendants of the added/removed nodes at the time of the
     * mutation. This returns a map from the "childList" mutations in a batch to
     * their respective added/removed trees.
     *
     * @param { NativeMutation[] } mutations
     * @returns { ChildListToTreesMap }
     */
    createChildListToTreesMap(mutations) {
        /** @type { ChildListToTreesMap } */
        const childListToTreesMap = new WeakMap();
        /** @type { WeakMap<Node, Node[]> } */
        const childListSnapshot = new WeakMap();
        /**
         * @param { Node } node
         * @returns { Node[] }
         */
        const getChildListSnapshot = (node) => childListSnapshot.get(node) || childNodes(node);
        /**
         * @param { Node } node
         * @returns { Tree }
         */
        const makeSnapshotTree = (node) => ({
            node,
            children: getChildListSnapshot(node).map(makeSnapshotTree),
        });
        /**
         * Reconstructs the child list before a mutation based on the state
         * after it and the child list modifications
         *
         * @param { Node[] } childListAfter
         * @param { NativeMutation } record
         * @returns { Node[] }
         */
        const reconstructChildList = (childListAfter, record) => {
            const { removedNodes, previousSibling, nextSibling } = record;
            const previousSiblingNodes = previousSibling
                ? childListAfter.slice(0, childListAfter.indexOf(previousSibling) + 1)
                : [];
            const nextSiblingNodes = nextSibling
                ? childListAfter.slice(childListAfter.indexOf(nextSibling))
                : [];
            return [...previousSiblingNodes, ...removedNodes, ...nextSiblingNodes];
        };
        mutations.toReversed().forEach((/** @type { NativeMutation } */ mutation) => {
            if (mutation.type === NATIVE_MUTATION_TYPES.CHILD_LIST) {
                childListToTreesMap.set(mutation, {
                    added: [...mutation.addedNodes].map(makeSnapshotTree),
                    removed: [...mutation.removedNodes].map(makeSnapshotTree),
                });
                // Update snapshot for previous mutations
                const childListAfterMutation = getChildListSnapshot(mutation.target);
                const childListBefore = reconstructChildList(childListAfterMutation, mutation);
                childListSnapshot.set(mutation.target, childListBefore);
            }
        });
        return childListToTreesMap;
    }

    /**
     * Turn `EditorMutation`s into `SerializedMutation`s by replacing their
     * references to nodes with node IDs and serialized trees.
     *
     * @param { EditorMutation[] } mutations
     * @returns { SerializedMutation[] }
     */
    serializeEditorMutations(mutations) {
        return mutations.flatMap((mutation) => {
            switch (mutation.type) {
                case EDITOR_MUTATION_TYPES.CHARACTER_DATA:
                case EDITOR_MUTATION_TYPES.CLASS_LIST:
                case EDITOR_MUTATION_TYPES.ATTRIBUTES: {
                    return this.serializeAttributesMutation(mutation);
                }
                case EDITOR_MUTATION_TYPES.ADD:
                case EDITOR_MUTATION_TYPES.REMOVE: {
                    const [nextNodeId, previousNodeId] = [
                        mutation.nextSibling,
                        mutation.previousSibling,
                    ].map((sibling) =>
                        // Preserve undefined and null values
                        sibling ? this.dependencies.domReferenceMap.getNodeId(sibling) : sibling
                    );
                    // Note: IDs are assigned to added nodes in `processChildListMutation`.
                    return {
                        type: mutation.type,
                        nodeId: this.dependencies.domReferenceMap.getNodeId(mutation.tree.node),
                        parentNodeId: this.dependencies.domReferenceMap.getNodeId(mutation.parent),
                        serializedNode: this.dependencies.domReferenceMap.serializeTree(
                            mutation.tree
                        ),
                        nextNodeId,
                        previousNodeId,
                    };
                }
                default: {
                    return mutation;
                }
            }
        });
    }

    /**
     * Take an attributes mutation, serialize it and return the result.
     *
     * @param { EditorMutation<"attributes"> | NativeMutation<"attributes"> } mutation
     * @returns { SerializedMutation<"attributes"> }
     */
    serializeAttributesMutation(mutation) {
        const nodeId = this.dependencies.domReferenceMap.getNodeId(mutation.target);
        return { ...omit(mutation, "target"), nodeId };
    }

    // ===========================
    // Commit application/reversal
    // ===========================

    /**
     * Take a batch of serialized mutations and apply them in the DOM, in order.
     *
     * @param { SerializedMutation[] } mutations
     * @param { Object } options
     * @param { boolean } options.ensureNewMutations whether to ensure new
     *        mutations are generated when applying the mutations
     * @param { boolean } options.areReversed whether the mutations are the
     *        reverse of other mutations
     */
    applyMutations(mutations, { ensureNewMutations = false, areReversed = false } = {}) {
        if (ensureNewMutations) {
            this.fixClassListMutationsToEnsureNewMutations(mutations);
        }
        for (const mutation of mutations) {
            switch (mutation.type) {
                case EDITOR_MUTATION_TYPES.CUSTOM: {
                    mutation.apply();
                    break;
                }
                case EDITOR_MUTATION_TYPES.CHARACTER_DATA: {
                    const node = this.dependencies.domReferenceMap.getNodeById(mutation.nodeId);
                    if (node) {
                        node.textContent = mutation.value;
                    }
                    break;
                }
                case EDITOR_MUTATION_TYPES.CLASS_LIST: {
                    const node = this.dependencies.domReferenceMap.getNodeById(mutation.nodeId);
                    if (node) {
                        toggleClass(node, mutation.className, mutation.value);
                    }
                    break;
                }
                case EDITOR_MUTATION_TYPES.ATTRIBUTES: {
                    const options = { ensureNewMutations, wasReversed: areReversed };
                    this.applyAttributesMutation(mutation, options);
                    break;
                }
                case EDITOR_MUTATION_TYPES.REMOVE: {
                    this.applyRemoveMutation(mutation);
                    break;
                }
                case EDITOR_MUTATION_TYPES.ADD: {
                    this.applyAddMutation(mutation);
                    break;
                }
            }
        }
    }

    /**
     * Take a serialized "attributes" mutation and apply it in the DOM.
     *
     * @param { SerializedMutation<"attributes"> } mutation
     * @param { Object } options
     * @param { boolean } [options.ensureNewMutations = false] whether the mutation is being used
     *        to create a new commit and requires to ensure new mutations are generated
     * @param { boolean } [options.wasReversed = false] whether the change was reversed
     */
    applyAttributesMutation(mutation, options = {}) {
        const node = this.dependencies.domReferenceMap.getNodeById(mutation.nodeId);
        if (node) {
            const value = this.processThrough(
                "attributes_mutation_value_processors",
                mutation.value,
                {
                    mutation,
                    ...options,
                }
            );
            if (!this.delegateTo("set_attribute_overrides", node, mutation.attributeName, value)) {
                if (value === null) {
                    node.removeAttribute(mutation.attributeName);
                } else {
                    node.setAttribute(mutation.attributeName, value);
                }
            }
        }
    }

    /**
     * Take a serialized "add" mutation and apply it in the DOM.
     *
     * @param { SerializedMutation<"add"> } mutation
     */
    applyAddMutation(mutation) {
        const { nodeId, serializedNode, parentNodeId, nextNodeId, previousNodeId } = mutation;

        let toAdd =
            this.dependencies.domReferenceMap.getNodeById(nodeId) ||
            this.dependencies.domReferenceMap.unserializeNode(serializedNode);
        toAdd = this.processThrough("add_node_mutation_processors", toAdd);
        if (!toAdd) {
            return;
        }

        const parent = this.dependencies.domReferenceMap.getNodeById(parentNodeId);
        if (!parent) {
            console.warn("Mutation could not be applied, parent node is missing.", mutation);
            return;
        }
        if (previousNodeId === null) {
            parent.prepend(toAdd);
            return;
        }
        if (nextNodeId === null) {
            parent.append(toAdd);
            return;
        }
        const isValid = (node) => node?.parentNode === parent;
        const previousNode = this.dependencies.domReferenceMap.getNodeById(previousNodeId);
        if (isValid(previousNode)) {
            previousNode.after(toAdd);
            return;
        }
        const nextNode = this.dependencies.domReferenceMap.getNodeById(nextNodeId);
        if (isValid(nextNode)) {
            nextNode.before(toAdd);
            return;
        }
        console.warn("Mutation could not be applied, reference nodes are invalid.", mutation);
    }

    /**
     * Take a serialized "remove" mutation and apply it in the DOM.
     *
     * @param { SerializedMutation<"remove"> } mutation
     */
    applyRemoveMutation(mutation) {
        const parent = this.dependencies.domReferenceMap.getNodeById(mutation.parentNodeId);
        const toRemove = this.dependencies.domReferenceMap.getNodeById(mutation.nodeId);
        if (!toRemove) {
            console.warn("Mutation could not be applied, node to remove is unknown.", mutation);
            return;
        }
        if (toRemove.parentElement !== parent) {
            console.warn("Mutation could not be applied, parent node does not match.", mutation);
            return;
        }
        toRemove.remove();
    }

    /**
     * Take a "custom" mutation and apply it in the DOM.
     *
     * @param { EditorMutation<"custom"> } mutation
     */
    applyCustomMutation(mutation) {
        mutation.apply();
        this.stageCustomMutation({ apply: mutation.apply, revert: mutation.revert });
    }

    /**
     * Take a batch of serialized mutations, reverse both their effect and their
     * order, then apply that.
     *
     * @param { SerializedMutation[] } mutations
     * @param { Object } [options]
     * @param { boolean } [options.ensureNewMutations = false] whether to ensure
     *        new mutations are generated when applying the mutations
     */
    revertMutations(mutations, { ensureNewMutations = false } = {}) {
        const reversedMutations = mutations.map((mutation) => {
            switch (mutation.type) {
                case EDITOR_MUTATION_TYPES.CHARACTER_DATA:
                case EDITOR_MUTATION_TYPES.CLASS_LIST:
                case EDITOR_MUTATION_TYPES.ATTRIBUTES:
                    return { ...mutation, value: mutation.oldValue, oldValue: mutation.value };
                case EDITOR_MUTATION_TYPES.REMOVE:
                    return { ...mutation, type: EDITOR_MUTATION_TYPES.ADD };
                case EDITOR_MUTATION_TYPES.ADD:
                    return { ...mutation, type: EDITOR_MUTATION_TYPES.REMOVE };
                case EDITOR_MUTATION_TYPES.CUSTOM:
                    return { ...mutation, apply: mutation.revert, revert: mutation.apply };
                default:
                    throw new Error(`Unknown mutation type: ${mutation.type}`);
            }
        });
        this.applyMutations(reversedMutations.toReversed(), {
            ensureNewMutations,
            areReversed: true,
        });
    }

    /**
     * When applying mutations for a new commit, we expect them to produce
     * observable mutations, which will then be stored in a new commit. However,
     * there are situations where applying a classList mutation would not
     * produce an observable mutation:
     * - adding a class that is already present
     * - removing a class that is already absent
     * These scenarios might happen due to the class having been already added
     * or removed by a previous unobserved mutation. We want, nevertheless to
     * produce the observable mutation of adding/removing this class, as this
     * does correspond to a state change in observable history and should be
     * included in the new commit. In order to produce such observable
     * mutations, we set the dom state to the one that would produce the desired
     * result. This is equivalent to restoring the dom to the observed state in
     * recorded history before applying a mutation, that is, oldValue (as
     * oldValue is always !value for staged classList records).
     *
     * @param { EditorMutation[] } mutations
     */
    fixClassListMutationsToEnsureNewMutations(mutations) {
        const isFirstOcurrence = trackOccurrencesPair();
        // Mutations that when applied would not produce observable classList mutations
        const nonObservableClassMutations = mutations
            .filter((mutation) => mutation.type === EDITOR_MUTATION_TYPES.CLASS_LIST)
            .filter(({ nodeId, className }) => isFirstOcurrence(nodeId, className))
            .map((mutation) => ({
                ...mutation,
                node: this.dependencies.domReferenceMap.getNodeById(mutation.nodeId),
            }))
            .filter(({ node, className, value }) => value === node?.classList.contains(className));
        if (nonObservableClassMutations.length) {
            const setToOldValue = ({ node, className, oldValue }) =>
                toggleClass(node, className, oldValue);

            // Set the non-observable class mutations to their old value,
            // without observing it.
            this.disconnect();
            nonObservableClassMutations.forEach(setToOldValue);
            this.observe();
        }
    }

    // =============
    // Miscellaneous
    // =============

    /**
     * Returns the deepest common ancestor element of the given mutations.
     *
     * @param { (EditorMutation)[] } mutations - The array of mutations.
     * @returns { HTMLElement | null } - The common ancestor element.
     */
    getMutationsCommonAncestor(mutations) {
        const nodes = mutations
            .map((m) => this.dependencies.domReferenceMap.getNodeById(m.parentNodeId || m.nodeId))
            .filter((node) => this.editable.contains(node));
        let commonAncestor = getCommonAncestor(nodes, this.editable);
        if (commonAncestor?.nodeType === Node.TEXT_NODE) {
            commonAncestor = commonAncestor.parentElement;
        }
        return commonAncestor;
    }

    /**
     * Trigger `on_content_updated_handlers` if there are staged mutations and
     * their targets have a common ancestor.
     */
    triggerContentUpdated() {
        // @todo @phoenix remove this?
        // @todo @phoenix this includes previous mutations that were already
        // stored in the current commit. Ideally, it should only include the new ones.
        const root = this.mutations.length && this.getMutationsCommonAncestor(this.mutations);
        if (root) {
            this.trigger("on_content_updated_handlers", root);
        }
    }
}

/**
 * @typedef { Object } OldValues
 * @property { Map<string, string> } attributes
 * @property { Map<string, boolean> } classList
 * @property { Map<string, string> } characterData
 */
/**
 * This class ensures mutation records have the correct historical `oldValue` by
 * checking against the last observed state.
 *
 * @see DomObserverPlugin.processNativeMutations
 *
 * - When mutations are observed, it is used to update a record's `oldValue`
 *   with the last observed state. @see apply
 * - When mutations are ignored, we store the record's `oldValue` for a node's
 *   attribute/class/textContent as the last observed value. @see store
 *   As multiple mutations to the same node-attribute/class/textContent can
 *   happen with the observer disabled, we store only the first value
 *   encountered for each node-attribute/class/text. This way, we capture the
 *   state as it was before any modification in the disabled observer sequence
 *   began.
 */
class OldValueManager {
    constructor() {
        this.reset();
    }

    reset() {
        /** @type { WeakMap<Node, OldValues> } */
        this.state = new WeakMap();
    }

    /**
     * Create a blank entry in the state for the given target, and return it.
     *
     * @param { Node } target
     * @returns { OldValues }
     */
    addTarget(target) {
        /** @type { OldValues } */
        const oldValues = {
            attributes: new Map(),
            classList: new Map(),
            characterData: new Map(),
        };
        this.state.set(target, oldValues);
        return oldValues;
    }

    /**
     * Store the `oldValue` property of the given mutation in the state for its
     * target if it doesn't have one yet.
     *
     * @param { NativeMutation<"attributes"|"characterData"> | EditorMutation<"classList"> } mutation
     */
    store(mutation) {
        const oldValues = this.state.get(mutation.target) || this.addTarget(mutation.target);
        const map = oldValues[mutation.type];
        const key = this.getMutationKey(mutation);
        // Only store it if not already stored.
        if (!map.has(key)) {
            map.set(key, mutation.oldValue);
        }
    }

    /**
     * Get the stored `oldValue` for the given mutation and return the mutation
     * object updated with that `oldValue` if found, unchanged otherwise.
     *
     * @template { NativeMutationType } T
     * @param { EditorMutation<T>} mutation
     * @returns { EditorMutation<T> }
     */
    apply(mutation) {
        const oldValues = this.state.get(mutation.target) || this.addTarget(mutation.target);
        const map = oldValues[mutation.type];
        const key = this.getMutationKey(mutation);
        if (map.has(key)) {
            const lastObservedValue = map.get(key);
            map.delete(key); // Remove entry, so it won't be used again.
            // Without removing the entry, the same historical value might be
            // incorrectly applied to future mutation records targeting the same
            // attribute/class of the same element, which would create incorrect
            // history mutations.
            return { ...mutation, oldValue: lastObservedValue };
        } else {
            return mutation;
        }
    }

    /**
     * Return the `OldValues` map key for the given mutation according to its type.
     *
     * @param { NativeMutation<"attributes"|"characterData"> | EditorMutation<"classList"> } mutation
     * @returns { string }
     */
    getMutationKey(mutation) {
        switch (mutation.type) {
            case NATIVE_MUTATION_TYPES.ATTRIBUTES:
                return mutation.attributeName;
            case EDITOR_MUTATION_TYPES.CLASS_LIST:
                return mutation.className;
            case NATIVE_MUTATION_TYPES.CHARACTER_DATA:
                return "textContent";
            default:
                throw new Error(`Unsupported mutation type: ${mutation.type}`);
        }
    }
}
