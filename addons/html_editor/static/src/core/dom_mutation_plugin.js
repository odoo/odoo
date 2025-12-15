import { Plugin } from "../plugin";
import { trackOccurrences, trackOccurrencesPair } from "@html_editor/utils/tracking";
import { treeToNodes, nodeToTree, NodeMap } from "@html_editor/utils/dom_info";
import { childNodes, descendants, getCommonAncestor } from "@html_editor/utils/dom_traversal";
import { omit, pick } from "@web/core/utils/objects";
import { toggleClass } from "@html_editor/utils/dom";
import { withSequence } from "@html_editor/utils/resource";

// The commit data keys handled by `DomMutation`.
const DOM_MUTATION_COMMIT_DATA_KEYS = [
    "mutations",
    "activeElementId",
    "selection",
    "selectionAfter",
];

/**
 * @typedef { string } NodeId
 *
 * @typedef { Object } SerializedNode
 * @property { number } nodeType
 * @property { NodeId } nodeId
 * @property { string } textValue
 * @property { string } tagName
 * @property { SerializedNode[] } children
 * @property { Record<string, string> } attributes
 *
 * @typedef { Object } SerializedSelection
 * @property { NodeId } anchorNodeId
 * @property { number } anchorOffset
 * @property { NodeId } focusNodeId
 * @property { number } focusOffset
 *
 * @typedef {Object} NativeMutationRecordClassList
 * @property { "classList" } type
 * @property { Node } target
 * @property { string } className
 * @property { boolean } oldValue
 * @property { boolean } value
 *
 * @typedef {Object} NativeMutationRecordAttributes
 * @property { "attributes" } type
 * @property { Node } target
 * @property { string } attributeName
 * @property { string } oldValue
 * @property { string } value
 *
 * @typedef {Object} NativeMutationRecordCharacterData
 * @property { "characterData" } type
 * @property { Node } target
 * @property { string } oldValue
 * @property { string } value
 *
 * @typedef {Object} Tree
 * @property {Node} node
 * @property {Tree[]} children
 *
 * @typedef {Object} NativeMutationRecordChildList
 * @property { "childList" } type
 * @property { Node } target
 * @property { Node } previousSibling
 * @property { Node } nextSibling
 * @property { Tree[] } addedTrees
 * @property { Tree[] } removedTrees
 *
 * @typedef { NativeMutationRecordClassList | NativeMutationRecordAttributes | NativeMutationRecordCharacterData | NativeMutationRecordChildList } EditorMutationRecord
 *
 * @typedef { Object } EditorMutationCharacterData
 * @property { "characterData" } type
 * @property { NodeId } nodeId
 * @property { string } value
 * @property { string } oldValue
 *
 * @typedef { Object } EditorMutationAttributes
 * @property { "attributes" } type
 * @property { NodeId } nodeId
 * @property { string } attributeName
 * @property { string } value
 * @property { string } oldValue
 *
 * @typedef { Object } EditorMutationClassList
 * @property { "classList" } type
 * @property { NodeId } nodeId
 * @property { string } className
 * @property { boolean } value
 * @property { boolean } oldValue
 *
 * @typedef { Object } EditorMutationAdd
 * @property { "add" } type
 * @property { NodeId } nodeId
 * @property { NodeId } parentNodeId
 * @property { SerializedNode } serializedNode
 * @property { NodeId } nextNodeId
 * @property { NodeId } previousNodeId
 *
 * @typedef { Object } EditorMutationRemove
 * @property { "remove" } type
 * @property { NodeId } nodeId
 * @property { NodeId } parentNodeId
 * @property { SerializedNode } serializedNode
 * @property { NodeId } nextNodeId
 * @property { NodeId } previousNodeId
 *
 * @typedef { EditorMutationCharacterData | EditorMutationAttributes | EditorMutationClassList | EditorMutationAdd | EditorMutationRemove } EditorMutation
 *
 * @typedef { Object } PreviewableOperation
 * @property { Function } commit
 * @property { Function } preview
 * @property { Function } revert
 *
 * @typedef { {
 *      authorTimestamp: number,              // timestamp of the commit authoring, before any mutation is applied
 *      mutations: EditorMutation[],          // the mutations to apply/revert
 *      activeElementId: NodeId,              // the ID of the active element before applying the mutations
 *      selection: SerializedSelection,       // the serialized selection before applying the mutations
 *      selectionAfter: SerializedSelection,  // the serialized selection after applying the mutations
 *      [key: string]: any,                   // additional properties
 * } } CommitData
 *
 * @typedef { string } CommitId
 *
 * @typedef { Object } EditorCommit
 * @property { CommitId } id
 * @property { CommitData } data
 * @property { Element } root the root of the changes in the commit
 */
/**
 * @typedef { Object } DomMutationShared
 * @property { DomMutationPlugin['commit'] } commit
 * @property { DomMutationPlugin['discard'] } discard
 * @property { DomMutationPlugin['stage'] } stage
 * @property { DomMutationPlugin['unstage'] } unstage
 * @property { DomMutationPlugin['stash'] } stash
 * @property { DomMutationPlugin['unstash'] } unstash
 * @property { DomMutationPlugin['update'] } update
 * @property { DomMutationPlugin['addCustomMutation'] } addCustomMutation
 * @property { DomMutationPlugin['applyCustomMutation'] } applyCustomMutation
 * @property { DomMutationPlugin['hasStagedMutations'] } hasStagedMutations
 * @property { DomMutationPlugin['ignoreDOMMutations'] } ignoreDOMMutations
 * @property { DomMutationPlugin['makePreviewableOperation'] } makePreviewableOperation
 * @property { DomMutationPlugin['makePreviewableAsyncOperation'] } makePreviewableAsyncOperation
 * @property { DomMutationPlugin['makeSavePoint'] } makeSavePoint
 * @property { DomMutationPlugin['createSnapshotCommit'] } createSnapshotCommit
 * @property { DomMutationPlugin['stageSelection'] } stageSelection
 * @property { DomMutationPlugin['stageFocus'] } stageFocus
 * @property { DomMutationPlugin['getIsPreviewing'] } getIsPreviewing
 */
/**
 * @typedef {((root: HTMLElement) => void)[]} content_updated_handlers
 * @typedef {(() => void)[]} restore_savepoint_handlers
 * @typedef {((node: Node, childTreesToSerialize: Tree[]) => Tree[])[]} serializable_descendants_processors
 * @typedef {(() => void)[]} before_commit_handlers
 */
export class DomMutationPlugin extends Plugin {
    static id = "domMutation";
    static dependencies = ["history", "selection", "sanitize"];
    static shared = [
        // Main
        "commit",
        "discard",
        "stage",
        "unstage",
        "stash",
        "unstash",
        "update",
        // From Original
        "addCustomMutation",
        "applyCustomMutation",
        "getIsPreviewing",
        "hasStagedMutations",
        "ignoreDOMMutations",
        "makePreviewableOperation",
        "makePreviewableAsyncOperation",
        "makeSavePoint",
        "createSnapshotCommit",
        "stageSelection",
        "stageFocus",
        // From DOM Map
        "getNodeById",
        "getNodeId",
        "serializeSelection",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        start_edition_handlers: () => {
            this.enableObserver();
        },
        before_history_reset_from_steps_handlers: () => {
            // TODO AGE: this is only to replace the `withObserverOff` call in
            // `history.resetFromSteps` but it's not useful for `history.reset`,
            // and assumes a call to `history_reset_from_steps_handlers` after.
            this.lastEnableObserverCallback = this.disableObserver();
        },
        history_reset_from_steps_handlers: () => {
            // See above.
            this.lastEnableObserverCallback?.();
            this.lastEnableObserverCallback = undefined;
        },
        history_reset_handlers: () => {
            this.dependencies.history.write(this.createSnapshotCommit(), "reset");
            this.stageSelection();
        },
        on_prepare_drag_handlers: this.disableHasStagedMutationsWarning.bind(this),
        history_cleaned_handlers: this.clean.bind(this),
        before_add_external_step_handlers: () => {
            // The last step is an uncommited draft, revert it first
            this.stash();
        },
        external_step_added_handlers: () => {
            // Reapply the uncommited draft, since this is not an operation which should cancel it
            this.unstash();
        },
        apply_commit_overrides: (commit) => {
            if (commit.data.mutations) {
                this.applyCommit(commit);
                return true;
            }
        },
        revert_commit_overrides: (commit, { ensureNewMutations = false } = {}) => {
            if (commit.data.mutations) {
                this.revertCommit(commit, { ensureNewMutations });
                return true;
            }
        },
        pre_undo_handlers: this.discardDraft.bind(this),
        post_undo_handlers: withSequence(0, (revertedStep) => {
            // TODO AGE: This used to be done in history after undo and
            // before dispatching post_undo_handlers. See if there is a
            // better way.
            // Consider the last position of the history as an undo.
            if (revertedStep) {
                // Include any commit data stored in the reverted step and that
                // is not handled by this plugin.
                // Note AGE: this is the `extraStepInfos` stuff.
                for (const [key, value] of Object.entries(revertedStep.commit.data)) {
                    if (!DOM_MUTATION_COMMIT_DATA_KEYS.includes(key)) {
                        this.update(key, value);
                    }
                }
                this.commit("undo");
            }
        }),
        pre_redo_handlers: this.discardDraft.bind(this),
        post_redo_handlers: withSequence(0, (revertedStep) => {
            // TODO AGE: This used to be done in history after redo and
            // before dispatching post_redo_handlers. See if there is a
            // better way.
            if (revertedStep) {
                // Include any commit data stored in the reverted step and that
                // is not handled by this plugin.
                // Note AGE: this is the `extraStepInfos` stuff.
                for (const [key, value] of Object.entries(revertedStep.commit.data)) {
                    if (!DOM_MUTATION_COMMIT_DATA_KEYS.includes(key)) {
                        this.update(key, value);
                    }
                }
                this.commit("redo");
            }
        }),
        node_by_id_providers: (nodeId) => this.getNodeById(nodeId),
    };

    setup() {
        this.nodeMap = new NodeMap();
        this.mutationFilteredClasses = new Set(this.getResource("system_classes"));
        this.mutationFilteredAttributes = new Set(this.getResource("system_attributes"));
        this.addGlobalDomListener("pointerup", (ev) => {
            if (this.editable.contains(ev.target)) {
                this.stageSelection();
            }
        });
        this.observer = new MutationObserver((records) => this.handleNewRecords(records));
        this.enableObserverCallbacks = new Set();
        this._cleanups.push(() => this.observer.disconnect());
        this.clean();
        /** @type { CommitData[] } */
        this.currentStash = [];
    }

    // TODO AGE: stepType should actually just be commit.type.
    commit(stepType) {
        const hasMutations = this.prepareForCommit(stepType || "original");
        if (!hasMutations) {
            // TODO: I isolated `prepareForCommit` for now for simplicity for me
            // but it's not clear with its return functions so it should not
            // remain this way.
            return false;
        }

        // AGE TODO: rename
        this.dispatchTo("before_commit_handlers", stepType); // making sure it updates the step we're adding
        const commit = this.createCommit();
        this.dependencies.history.write(commit, stepType);

        this.resetCurrentMutations();

        this.stageSelection();
        this.config.onChange?.({ isPreviewing: this.isPreviewing });
        return commit;
    }

    discard() {
        if (!this.prepareForCommit()) {
            // TODO: not sure it's needed here. If not, probably better not to
            // make a commit and just to call revert directly.
            return;
        }
        this.revertChanges(this.createCommit().data);
    }

    /**
     * @param { EditorMutationRecord[] } records
     */
    stage(records) {
        // AGE note: is eventually called when calling `handleObserverRecords`.
        // Maybe `handleObserverRecords` is the higher level function then?
        for (const record of records) {
            switch (record.type) {
                case "characterData":
                case "classList":
                case "attributes": {
                    const nodeId = this.getNodeId(record.target);
                    this.currentChanges.mutations.push({ ...omit(record, "target"), nodeId });
                    break;
                }
                case "childList": {
                    this.currentChanges.mutations.push(...this.splitChildListRecord(record));
                    break;
                }
            }
        }
    }

    unstage(changes) {}

    stash() {
        this.currentStash.push(this.discardDraft());
    }

    unstash(index = -1) {
        if (this.currentStash.length > index) {
            const changes = this.currentStash.splice(index, 1)[0];
            this.applyMutations(changes.mutations);
            if (this.isObserverDisabled) {
                // Make sure the unstashed mutations are recorded.
                this.currentChanges.mutations.push(...changes.mutations);
            }
            // TODO AGE: shouldn't this also apply other changes?
        }
    }

    /**
     * Set a key/value pair in the data of the next commit.
     *
     * @param {string} key
     * @param {any} value
     */
    update(key, value) {
        if (key in DOM_MUTATION_COMMIT_DATA_KEYS) {
            console.warn("Can't update a reserved commit data key.");
        } else {
            this.currentChanges[key] = value;
        }
    }

    // Private

    clean() {
        /** @type { CommitData } */
        this.currentChanges = {
            authorTimestamp: Date.now(),
            mutations: [],
            activeElementId: null,
            selection: {},
            selectionAfter: null,
        };
        /** @type { WeakMap<Node, { attributes: Map<string, string>, classList: Map<string, boolean>, characterData: Map<string, string> }> } */
        this.lastObservedState = new WeakMap();
        this.nodeMap = new NodeMap();
        this.setNodeId(this.editable);
    }

    /**
     * Set a key/value pair in the data of the next commit, allowing changes to
     * locally managed keys.
     *
     * Note AGE: Maybe not needed but right now I want to play it safe.
     *
     * @param {string} key
     * @param {any} value
     */
    updateLocal(key, value) {
        this.currentChanges[key] = value;
    }

    resetCurrentMutations() {
        this.updateLocal("mutations", []);
        this.updateLocal("authorTimestamp", Date.now());
    }

    // DOM Map

    /**
     * @param {NodeId} id
     * @returns {Node | undefined}
     */
    getNodeById(id) {
        return this.nodeMap.getNode(id);
    }

    /**
     * @param {Node} node
     * @returns {NodeId}
     */
    getNodeId(node) {
        return this.nodeMap.getId(node);
    }

    /**
     * @param { Node } node
     */
    setNodeId(node) {
        let id = this.nodeMap.getId(node);
        if (!id) {
            id = node === this.editable ? "root" : this.generateId();
            this.nodeMap.set(id, node);
            node = node.firstChild;
            while (node) {
                this.setNodeId(node);
                node = node.nextSibling;
            }
        }
        return id;
    }

    /**
     * Serialize an editor selection.
     * @param { EditorSelection } selection
     * @returns { SerializedSelection }
     */
    serializeSelection(selection) {
        return {
            anchorNodeId: this.getNodeId(selection.anchorNode),
            anchorOffset: selection.anchorOffset,
            focusNodeId: this.getNodeId(selection.focusNode),
            focusOffset: selection.focusOffset,
        };
    }

    /**
     * Serialize a node and its children.
     *
     * @param { Node } node
     * @returns {SerializedNode|null}
     */
    serializeNode(node) {
        return this.serializeTree(nodeToTree(node));
    }

    /**
     * @param {Tree} tree
     * @returns {SerializedNode|null}
     */
    serializeTree(tree) {
        const node = tree.node;
        const nodeId = this.getNodeId(node);
        if (!nodeId) {
            return null;
        }
        const result = {
            nodeType: node.nodeType,
            nodeId: nodeId,
        };
        if (node.nodeType === Node.TEXT_NODE) {
            result.textValue = node.nodeValue;
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            let childTreesToSerialize = tree.children;
            for (const cb of this.getResource("serializable_descendants_processors")) {
                childTreesToSerialize = cb(node, childTreesToSerialize);
            }
            result.tagName = node.tagName;
            result.attributes = Object.fromEntries(
                [...node.attributes].map((attr) => [attr.name, attr.value])
            );
            result.children = childTreesToSerialize
                .map((tree) => this.serializeTree(tree))
                .filter(Boolean);
        }
        return result;
    }

    /**
     * Unserialize a node and its children.
     *
     * @param { SerializedNode } node
     * @returns { Node }
     */
    unserializeNode(node) {
        let [unserializedNode, newNodesMap] = this._unserializeNode(node, this.nodeMap);
        if (!unserializedNode) {
            return null;
        }
        const fakeNode = this.document.createElement("fake-el");
        // TODO AGE: this next line has the effect of REMOVING THE NODE FROM THE
        // DOM! Is that intended?
        fakeNode.appendChild(unserializedNode);
        this.dependencies.sanitize.sanitize(fakeNode, { IN_PLACE: true });
        unserializedNode = fakeNode.firstChild;
        if (!unserializedNode) {
            return null;
        }
        // Only assing id to the remaining nodes, otherwise the removed nodes
        // will still be accessible through the nodeMap and could lead to
        // security issues.
        for (const node of [unserializedNode, ...descendants(unserializedNode)]) {
            if (this.nodeMap.hasNode(node)) {
                continue;
            }
            const id = newNodesMap.get(node);
            if (id) {
                this.nodeMap.set(id, node);
            }
        }
        return unserializedNode;
    }

    /**
     * Unserialize a node and its children.
     * @param { SerializedNode } serializedNode
     * @param { Map<Node, string> } _map
     * @returns { [Node, Map<Node, string>] }
     */
    _unserializeNode(serializedNode, nodeMap = new NodeMap(), _map = new Map()) {
        let node = nodeMap.getNode(serializedNode.nodeId);
        if (node) {
            return [node, _map];
        }
        if (serializedNode.nodeType === Node.TEXT_NODE) {
            node = this.document.createTextNode(serializedNode.textValue);
        } else if (serializedNode.nodeType === Node.ELEMENT_NODE) {
            node = this.document.createElement(serializedNode.tagName);
            for (const key in serializedNode.attributes) {
                node.setAttribute(key, serializedNode.attributes[key]);
            }
            node.append(
                ...serializedNode.children
                    .map((child) => this._unserializeNode(child, nodeMap, _map)[0])
                    .filter(Boolean)
            );
        } else {
            console.warn("unknown node type");
            return [null, _map];
        }
        _map.set(node, serializedNode.nodeId);
        return [node, _map];
    }

    // NEW: Commit creation

    prepareForCommit(stepType) {
        this.handleObserverRecords(true, stepType);
        const currentMutationsCount = this.currentChanges.mutations.length;
        if (currentMutationsCount === 0) {
            return false;
        }
        const commitRoot = this.getMutationsRoot(this.currentChanges.mutations) || this.editable;
        this.dispatchTo("normalize_handlers", commitRoot, stepType);
        this.handleObserverRecords(false, stepType);
        if (currentMutationsCount === this.currentChanges.mutations.length) {
            // If there was no registered mutation during the normalization step,
            // force the dispatch of a content_updated to allow i.e. the hint
            // plugin to react to non-observed changes (i.e. a div becoming
            // a baseContainer).
            this.dispatchContentUpdated();
        }
        return true;
    }

    // TODO: rename
    discardDraft() {
        /** @type { CommitData } */
        const changes = { ...this.currentChanges };
        // Discard current draft.
        this.handleObserverRecords();
        this.revertMutations(this.currentChanges.mutations);
        this.observer.takeRecords();
        this.resetCurrentMutations();
        return changes;
    }

    /**
     * @returns {EditorMutationCommit}
     */
    createCommit() {
        this.updateLocal(
            "selectionAfter",
            this.serializeSelection(this.dependencies.selection.getEditableSelection())
        );
        const data = { ...this.currentChanges };
        return {
            id: this.generateId(),
            data,
            root: this.getNodeId(this.getMutationsRoot(data.mutations) || this.editable),
        };
    }

    /**
     * @returns {EditorMutationCommit}
     */
    createSnapshotCommit() {
        const authorTimestamp = this.currentChanges.authorTimestamp || Date.now();
        return {
            id: this.dependencies.history.getHistorySteps().at(-1)?.id || this.generateId(),
            data: {
                authorTimestamp,
                mutations: childNodes(this.editable)
                    .filter((node) => this.nodeMap.hasNode(node))
                    .map((node) => ({
                        type: "add",
                        parentNodeId: "root",
                        nodeId: this.getNodeId(node),
                        serializedNode: this.serializeNode(node),
                        nextNodeId: null,
                    })),
                activeElementId: null,
                selection: {
                    anchorNode: undefined,
                    anchorOffset: undefined,
                    focusNode: undefined,
                    focusOffset: undefined,
                },
                selectionAfter: null,
            },
            root: this.getNodeId(this.editable),
        };
    }

    // NEW: Apply mutations

    applyCommit(commit) {
        this.applyMutations(commit.data.mutations);
        // TODO AGE: shouldn't this also apply other changes?
    }

    revertCommit(commit, { ensureNewMutations = false } = {}) {
        this.revertChanges(commit.data, { ensureNewMutations });
    }

    /**
     * @param {CommitData} param0
     */
    revertChanges(
        { mutations, activeElementId, selection, selectionAfter },
        { ensureNewMutations = false } = {}
    ) {
        this.revertMutations(mutations, { ensureNewMutations });
        this.setSerializedFocus(activeElementId);
        this.stageFocus();
        this.setSerializedSelection(selection);
        this.updateLocal("selection", selectionAfter);
    }

    /**
     * @param {EditorMutation[]} mutations
     */
    revertMutations(mutations, { ensureNewMutations = false } = {}) {
        const revertedMutations = mutations.map((mutation) => {
            switch (mutation.type) {
                case "characterData":
                case "classList":
                case "attributes":
                    return { ...mutation, value: mutation.oldValue, oldValue: mutation.value };
                case "remove":
                    return { ...mutation, type: "add" };
                case "add":
                    return { ...mutation, type: "remove" };
                case "custom":
                    return { ...mutation, apply: mutation.revert, revert: mutation.apply };
                default:
                    throw new Error(`Unknown mutation type: ${mutation.type}`);
            }
        });
        this.applyMutations(revertedMutations.toReversed(), { ensureNewMutations, reverse: true });
    }

    /**
     * @param {EditorMutation[]} mutations
     * @param { Object } options
     * @param { boolean } options.ensureNewMutations whether to ensure new
     *        mutations are generated when applying the mutations
     * @param { boolean } options.reverse whether the mutations are the reverse
     *        of other mutations
     */
    applyMutations(mutations, { ensureNewMutations = false, reverse = false } = {}) {
        if (ensureNewMutations) {
            this.fixClassListMutationsToEnsureNewMutations(mutations);
        }
        for (const mutation of mutations) {
            switch (mutation.type) {
                case "custom": {
                    mutation.apply();
                    break;
                }
                case "characterData": {
                    const node = this.getNodeById(mutation.nodeId);
                    if (node) {
                        node.textContent = mutation.value;
                    }
                    break;
                }
                case "classList": {
                    const node = this.getNodeById(mutation.nodeId);
                    if (node) {
                        toggleClass(node, mutation.className, mutation.value);
                    }
                    break;
                }
                case "attributes": {
                    const node = this.getNodeById(mutation.nodeId);
                    if (node) {
                        let value = mutation.value;
                        for (const cb of this.getResource("attribute_change_processors")) {
                            value = cb(
                                {
                                    target: node,
                                    attributeName: mutation.attributeName,
                                    oldValue: mutation.oldValue,
                                    value,
                                    reverse,
                                },
                                { ensureNewMutations }
                            );
                        }
                        this.setAttribute(node, mutation.attributeName, value);
                    }
                    break;
                }
                case "remove": {
                    this.applyRemoveMutation(mutation);
                    break;
                }
                case "add": {
                    this.applyAddMutation(mutation);
                    break;
                }
            }
        }
    }

    /**
     * @param { Node } node
     * @param { string } attributeName
     * @param { string } attributeValue
     */
    setAttribute(node, attributeName, attributeValue) {
        if (this.delegateTo("set_attribute_overrides", node, attributeName, attributeValue)) {
            return;
        }

        // if attributeValue is falsy but not null, we still need to apply it
        if (attributeValue !== null) {
            node.setAttribute(attributeName, attributeValue);
        } else {
            node.removeAttribute(attributeName);
        }
    }

    /**
     * @param {EditorMutationAdd} mutation
     */
    applyAddMutation(mutation) {
        const { nodeId, serializedNode, parentNodeId, nextNodeId, previousNodeId } = mutation;

        const toAdd = this.getNodeById(nodeId) || this.unserializeNode(serializedNode);
        if (!toAdd) {
            return;
        }

        const parent = this.getNodeById(parentNodeId);
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
        const previousNode = this.getNodeById(previousNodeId);
        if (isValid(previousNode)) {
            previousNode.after(toAdd);
            return;
        }
        const nextNode = this.getNodeById(nextNodeId);
        if (isValid(nextNode)) {
            nextNode.before(toAdd);
            return;
        }
        console.warn("Mutation could not be applied, reference nodes are invalid.", mutation);
    }

    /**
     * @param {EditorMutationRemove} mutation
     */
    applyRemoveMutation(mutation) {
        const parent = this.getNodeById(mutation.parentNodeId);
        const toRemove = this.getNodeById(mutation.nodeId);
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
     * @param { SerializedSelection } selection
     */
    setSerializedSelection(selection) {
        if (!selection.anchorNodeId) {
            return;
        }
        const anchorNode = this.getNodeById(selection.anchorNodeId);
        if (!anchorNode) {
            return;
        }
        const newSelection = {
            anchorNode,
            anchorOffset: selection.anchorOffset,
        };
        const focusNode = this.getNodeById(selection.focusNodeId);
        if (focusNode) {
            newSelection.focusNode = focusNode;
            newSelection.focusOffset = selection.focusOffset;
        }
        this.dependencies.selection.setSelection(newSelection, { normalize: false });
        // @todo @phoenix add this in the selection or table plugin.
        // // If a table must be selected, ensure it's in the same tick.
        // this._handleSelectionInTable();
    }

    /**
     * @param { NodeId } activeElementId
     */
    setSerializedFocus(activeElementId) {
        const elementToFocus =
            activeElementId === "root"
                ? this.editable
                : activeElementId && this.getNodeById(activeElementId);
        if (elementToFocus?.isConnected && elementToFocus !== this.document.activeElement) {
            elementToFocus.focus();
        }
    }

    // Observer stuff

    enableObserver() {
        this.observer.observe(this.editable, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeOldValue: true,
            characterData: true,
            characterDataOldValue: true,
        });
    }

    /**
     * Disable the mutation observer.
     *
     * /!\ This method should be used with extreme caution. Not observing some
     * mutations could lead to mutations that are impossible to undo/redo.
     */
    disableObserver() {
        const enableObserver = () => {
            this.enableObserverCallbacks.delete(enableObserver);
            if (this.enableObserverCallbacks.size > 0) {
                return;
            }
            this.handleObserverRecords();
            this.isObserverDisabled = false;
        };
        this.enableObserverCallbacks.add(enableObserver);
        this.handleObserverRecords();
        this.isObserverDisabled = true;
        return enableObserver;
    }

    /**
     * This is not shared as it is only used internally by the DOM mutation plugin.
     * Other plugins should use {@link ignoreDOMMutations} instead.
     * TODO AGE: why do we need this _and_ disableObserver?
     */
    withObserverOff(callback) {
        this.handleObserverRecords();
        this.observer.disconnect();
        callback();
        this.enableObserver();
    }

    /**
     * Execute {@link callback} while the MutationObserver is disabled.
     *
     * /!\ This method should be used with extreme caution. Not observing some
     * mutations could lead to mutations that are impossible to undo/redo.
     *
     * /!\ Do not re-introduce nodes that had been already added to the DOM in
     * a commit. @see isObservedNode
     *
     * @param {Function} callback
     */
    ignoreDOMMutations(callback) {
        const enableObserver = this.disableObserver();
        try {
            return callback();
        } finally {
            enableObserver();
        }
    }

    /**
     * Any node that was added to the DOM without a mutation record in a commit
     * (typically due to {@link ignoreDOMMutations}) is considered an unobserved
     * node.
     *
     * A known limitation to this approach is when a node that had been present
     * in the editable before (and thus has an entry in the nodeMap) is re-added
     * with {@link ignoreDOMMutations}. Such node will not be flagged as
     * unobserved and history might become inconsistent.
     *
     * @param {Node} node
     * @returns {boolean}
     */
    isObservedNode(node) {
        return this.nodeMap.hasNode(node);
    }

    disableHasStagedMutationsWarning() {
        this.ignoreHasStagedMutations = true;
        return () => {
            this.ignoreHasStagedMutations = false;
        };
    }

    hasStagedMutations() {
        if (this.ignoreHasStagedMutations) {
            return false;
        }
        return !!this.currentChanges.mutations.find((m) =>
            ["characterData", "remove", "add"].includes(m.type)
        );
    }

    // New mutations

    handleObserverRecords(dispatch = true, stepType) {
        this.handleNewRecords(this.observer.takeRecords(), dispatch, stepType);
    }

    /**
     * @param { NativeMutationRecord[] } records
     * @param { boolean } [dispatch]
     * @param { import("./history_plugin").HistoryStepType } [currentOperation] the type
     * of the step we're about to write (TODO AGE: obviously this is wrong)
     */
    handleNewRecords(records, dispatch = true, currentOperation) {
        const processedRecords = this.processNewRecords(records);
        if (processedRecords.length) {
            // TODO modify `handleMutations` of web_studio to handle
            // `undoOperation`
            if (dispatch) {
                this.dispatchTo("handleNewRecords", processedRecords, currentOperation);
            }
            // Process potential new records adds by handleNewRecords.
            // TODO AGE: shouldn't this be in the if then?
            this.processNewRecords(this.observer.takeRecords());
            this.dispatchContentUpdated();
        }
    }

    /**
     * Transforms NativeMutationRecords into EditorMutationRecords.
     *
     * ChildList record have added/removed trees added to them.
     * Class attribute records are expanded into multiple classList records.
     * Attribute records have their oldValue normalized and new value added to it.
     * CharacterData records have the new value added to it.
     *
     * @param {NativeMutationRecord[]} records
     * @returns {EditorMutationRecord[]}
     */
    transformToEditorMutationRecords(records) {
        records = this.transformChildListRecords(records);
        return records.flatMap((record) => {
            if (record.type === "attributes") {
                if (record.attributeName === "class") {
                    return this.splitClassMutationRecord(record);
                }
                const oldValue = record.oldValue === undefined ? null : record.oldValue;
                const value = record.target.getAttribute(record.attributeName);
                return { ...pick(record, "type", "target", "attributeName"), oldValue, value };
            }
            if (record.type === "characterData") {
                const value = record.target.textContent;
                return { ...pick(record, "type", "target", "oldValue"), value };
            }
            return record;
        });
    }

    /**
     * @param { NativeMutationRecord[] } mutations
     * @returns { EditorMutationRecord[] }
     */
    processNewRecords(mutations) {
        if (this.observer.takeRecords().length) {
            throw new Error("MutationObserver has pending records");
        }
        // Filter.
        mutations = this.filterAttributeMutationRecords(mutations);
        mutations = this.filterSameTextContentMutationRecords(mutations);
        mutations = this.filterOutIntermediateStateMutationRecords(mutations);
        // Transform.
        let records = this.transformToEditorMutationRecords(mutations);
        // Filter some more and adjust.
        records = records.filter((record) => !this.isSystemMutationRecord(record));
        records = this.filterAndAdjustEditorMutationRecords(records);
        this.stage(records);
        records
            .filter(({ type }) => type === "attributes")
            .forEach((record) => this.dispatchTo("attribute_change_handlers", record));
        return records;
    }

    // Mutations filtering/processing

    /**
     * If the observer is disabled, store the last observed state of the
     * target's affected property (attribute/class/textContent) and drop the
     * record.
     *
     * Otherwise (observer enabled), update the record as follows:
     * - mutations targeting an unobserved node are dropped
     * - mutations of type "attributes", "classList", and "characterData" have
     * their `oldValue` adjusted to the last observed state of that target's
     * property
     * - mutations of type "childList" are updated to not include references to
     * unobserved nodes.
     *
     * @param {EditorMutationRecord[]} records
     * @returns {EditorMutationRecord[]}
     */
    filterAndAdjustEditorMutationRecords(records) {
        this.dispatchTo("before_filter_mutation_record_handlers", records);
        const savableRecordPredicates = this.getResource("savable_mutation_record_predicates");
        const isRecordSavable = (record) => savableRecordPredicates.every((p) => p(record));
        const result = [];
        for (const record of records) {
            if (!this.isObservedNode(record.target)) {
                continue;
            }
            if (this.isObserverDisabled || !isRecordSavable(record)) {
                if (record.type !== "childList") {
                    this.storeOldValue(record);
                }
                continue;
            }
            const updatedRecord =
                record.type === "childList"
                    ? this.updateChildListRecord(record)
                    : this.updateOldValue(record);
            if (this.isValidRecord(updatedRecord)) {
                if (record.type === "childList") {
                    record.addedTrees
                        .flatMap(treeToNodes)
                        .filter((node) => !this.nodeMap.hasNode(node))
                        .forEach((node) => this.nodeMap.set(this.generateId(), node));
                }
                result.push(updatedRecord);
            }
        }
        return result;
    }

    /**
     * @param {EditorMutationRecord} record
     */
    isValidRecord(record) {
        switch (record.type) {
            case "attributes":
            case "classList":
            case "characterData":
                // Filter out no-op
                return record.value !== record.oldValue;
            case "childList":
                return (
                    // Filter out no-op
                    (record.addedTrees.length || record.removedTrees.length) &&
                    // Filter out mutation without a valid position for node insertion
                    (record.previousSibling !== undefined || record.nextSibling !== undefined)
                );
        }
    }

    /**
     * @param { EditorMutationRecord } record
     */
    isSystemMutationRecord(record) {
        if (record.type === "attributes") {
            return this.mutationFilteredAttributes.has(record.attributeName);
        }
        if (record.type === "classList") {
            return this.mutationFilteredClasses.has(record.className);
        }
        return false;
    }

    /**
     * @param {NativeMutationRecordChildList} record
     * @returns { (EditorMutationRemove|EditorMutationAdd)[] }
     */
    splitChildListRecord(record) {
        const parentNodeId = this.getNodeId(record.target);
        if (!parentNodeId) {
            throw new Error("Unknown parent node");
        }

        const makeSingleNodeRecords = (trees, type) =>
            trees.map((tree, index, treeList) => {
                const node = tree.node;
                const nodeList = treeList.map((t) => t.node);
                const [previousSibling, nextSibling] =
                    type === "add"
                        ? [nodeList[index - 1] || record.previousSibling, record.nextSibling]
                        : [record.previousSibling, nodeList[index + 1] || record.nextSibling];
                const [nextNodeId, previousNodeId] = [nextSibling, previousSibling].map((sibling) =>
                    // Preserve undefined and null values
                    sibling ? this.getNodeId(sibling) : sibling
                );
                const nodeId = this.getNodeId(node);
                const serializedNode = this.serializeTree(tree);
                return { type, nodeId, parentNodeId, serializedNode, nextNodeId, previousNodeId };
            });

        return [
            ...makeSingleNodeRecords(record.removedTrees, "remove"),
            ...makeSingleNodeRecords(record.addedTrees, "add"),
        ];
    }

    /**
     * ChildList mutation records do not contain information about the
     * descendants of the added/removed nodes at the time of the mutation. This
     * method transforms childList mutation records to include information about
     * the added/removed trees.
     *
     * @param {NativeMutationRecord[]} records
     * @returns {(EditorMutationRecord|NativeMutationRecord)[]}
     */
    transformChildListRecords(records) {
        /** @type {WeakMap<Node, Node[]>} */
        const childListSnapshot = new WeakMap();
        /** @type {(node: Node) => Node[]} */
        const getChildListSnapshot = (node) => childListSnapshot.get(node) || childNodes(node);
        /** @type {(node: Node) => Tree} */
        const makeSnapshotTree = (node) => ({
            node,
            children: getChildListSnapshot(node).map(makeSnapshotTree),
        });

        // Reconstructs the child list before a mutation based on the state
        // after it and the child list modifications
        /** @type {(childListAfter: Node[], record: NativeMutationRecord) => Node[]} */
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

        return records
            .toReversed()
            .map((/** @type {NativeMutationRecord} */ record) => {
                if (record.type !== "childList") {
                    return record;
                }
                const transformedRecord = {
                    ...pick(record, "type", "previousSibling", "nextSibling", "target"),
                    addedTrees: [...record.addedNodes].map(makeSnapshotTree),
                    removedTrees: [...record.removedNodes].map(makeSnapshotTree),
                };
                // Update snapshot for previous mutations
                const childListAfterMutation = getChildListSnapshot(record.target);
                const childListBefore = reconstructChildList(childListAfterMutation, record);
                childListSnapshot.set(record.target, childListBefore);
                return transformedRecord;
            })
            .toReversed();
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
            .filter((mutation) => mutation.type === "classList")
            .filter(({ nodeId, className }) => isFirstOcurrence(nodeId, className))
            .map((mutation) => ({
                ...mutation,
                node: this.getNodeById(mutation.nodeId),
            }))
            .filter(({ node, className, value }) => value === node?.classList.contains(className));
        if (nonObservableClassMutations.length) {
            const setToOldValue = ({ node, className, oldValue }) =>
                toggleClass(node, className, oldValue);
            this.withObserverOff(() => nonObservableClassMutations.forEach(setToOldValue));
        }
    }

    dispatchContentUpdated() {
        if (!this.currentChanges.mutations.length) {
            return;
        }
        // @todo @phoenix remove this?
        // @todo @phoenix this includes previous mutations that were already
        // stored in the current commit. Ideally, it should only include the new ones.
        const root = this.getMutationsRoot(this.currentChanges.mutations);
        if (!root) {
            return;
        }
        this.dispatchTo("content_updated_handlers", root);
    }

    /**
     * @param { NativeMutationRecord[] } records
     */
    filterAttributeMutationRecords(records) {
        return records.filter((record) => {
            if (record.type !== "attributes") {
                return true;
            }
            // Skip the attributes change on the dom.
            if (record.target === this.editable) {
                return false;
            }
            if (record.attributeName === "contenteditable") {
                return false;
            }
            return true;
        });
    }

    /**
     * @param { NativeMutationRecord[] } records
     * @returns { NativeMutationRecord[] }
     */
    filterSameTextContentMutationRecords(records) {
        const filteredRecords = [];
        for (const record of records) {
            if (record.type === "childList" && this.isSameTextContentMutation(record)) {
                const { addedNodes, removedNodes } = record;
                const oldId = this.getNodeId(removedNodes[0]);
                if (oldId) {
                    this.nodeMap.set(oldId, addedNodes[0]);
                    continue;
                }
            }
            filteredRecords.push(record);
        }
        return filteredRecords;
    }

    /**
     * @param {NativeMutationRecordChildList} record
     * @returns {NativeMutationRecordChildList}
     */
    updateChildListRecord(record) {
        // Invalidate sibling references to unobserved nodes
        const isValidReference = (node) => node === null || this.isObservedNode(node);
        const updateSibling = (sibling) => (isValidReference(sibling) ? sibling : undefined);
        const previousSibling = updateSibling(record.previousSibling);
        const nextSibling = updateSibling(record.nextSibling);

        // Filter out unobserved nodes in removedTrees
        const removeUnobservedNodes = (tree) => {
            if (!this.isObservedNode(tree.node)) {
                return null;
            }
            return {
                node: tree.node,
                children: tree.children.map(removeUnobservedNodes).filter(Boolean),
            };
        };
        const removedTrees = record.removedTrees.map(removeUnobservedNodes).filter(Boolean);

        return {
            ...record,
            previousSibling,
            nextSibling,
            removedTrees,
        };
    }

    /**
     * Check if a mutation consists of removing and adding a single text node
     * with the same text content, which occurs in Firefox but is optimized
     * away in Chrome.
     *
     * @param { NativeMutationRecord } record
     */
    isSameTextContentMutation(record) {
        const { addedNodes, removedNodes } = record;
        return (
            record.type === "childList" &&
            addedNodes.length === 1 &&
            removedNodes.length === 1 &&
            addedNodes[0].nodeType === Node.TEXT_NODE &&
            removedNodes[0].nodeType === Node.TEXT_NODE &&
            addedNodes[0].textContent === removedNodes[0].textContent
        );
    }

    /**
     * Mutation records of type "attribute" and "characterData" provide the old
     * value, but not the new value. When multiple mutations occur in the same
     * batch for an element's attribute or characterData, we only know the final
     * value of the accumulated changes, which is the DOM's current state.
     *
     *  The oldValue provided by mutations after the first one are intermediate
     *  states that we do not care about. Discarding them allows us to store a
     *  single record representing the accumulated changes, instead of
     *  reconstructing the new value introduced by each mutation.
     *
     * @param { NativeMutationRecord[] } records
     */
    filterOutIntermediateStateMutationRecords(records) {
        // Keep track of visited attributes per each node
        const isFirstAttributeOccurrence = trackOccurrencesPair();
        // Keep track of visited nodes for characterData mutations
        const isFirstCharDataOccurence = trackOccurrences();
        const filteredRecords = [];
        for (const record of records) {
            if (record.type === "attributes") {
                // Keep only the first mutation record for each (node, attribute) pair.
                if (isFirstAttributeOccurrence(record.target, record.attributeName)) {
                    filteredRecords.push(record);
                }
            } else if (record.type === "characterData") {
                // Keep only the first charData mutation record for each node.
                if (isFirstCharDataOccurence(record.target)) {
                    filteredRecords.push(record);
                }
            } else {
                filteredRecords.push(record);
            }
        }
        return filteredRecords;
    }

    /**
     * Breaks down a class attribute mutation into individual class
     * addition/removal records for more precise history tracking.
     *
     * @param { NativeMutationRecord } record of type "attributes" with attributeName === "class"
     * @returns { NativeMutationRecordClassList[]}
     */
    splitClassMutationRecord(record) {
        // oldValue can be nullish, or have extra spaces
        const oldValue = record.oldValue?.split(" ").filter(Boolean);
        const classesBefore = new Set(oldValue);
        const classesAfter = new Set(record.target.classList);
        // @todo: use Set.prototype.difference when it becomes widely available
        const setDifference = (setA, setB) => {
            const diff = new Set(setA);
            setB.forEach((item) => diff.delete(item));
            return diff;
        };
        const addedClasses = setDifference(classesAfter, classesBefore);
        const removedClasses = setDifference(classesBefore, classesAfter);

        /** @type {(className: string, isAdded: boolean) => NativeMutationRecordClassList } */
        const createClassRecord = (className, isAdded) => ({
            type: "classList",
            target: record.target,
            className,
            value: isAdded,
            oldValue: !isAdded,
        });
        // Generate records for each class change
        return [
            ...[...addedClasses].map((cls) => createClassRecord(cls, true)),
            ...[...removedClasses].map((cls) => createClassRecord(cls, false)),
        ];
    }

    // State storage stuff

    /**
     * This function, alongside @see updateOldValue, ensures mutation records
     * have the correct historical "oldValue" by checking against the last
     * observed state.
     *
     * When the observer is disabled, we store the record's `oldValue` for a
     * node's attribute/class/textContent as the last observed value.
     *
     * As multiple mutations to the same node-attribute/class/textContent can
     * happen with the observer disabled, we store only the first value
     * encountered for each node-attribute/class/text. This way, we capture the
     * state as it was before any modifications in the disabled observer
     * sequence began.
     *
     * @see updateOldValue
     *
     * @param {NativeMutationRecordAttributes|NativeMutationRecordClassList|NativeMutationRecordCharacterData} record
     */
    storeOldValue(record) {
        const { stateMap, key } = this.getObservedStateStorage(record);
        // Only store it if not already stored.
        if (!stateMap.has(key)) {
            stateMap.set(key, record.oldValue);
        }
    }

    /**
     * @param {EditorMutationRecord} record
     * @returns { { stateMap: Map, key: string } }
     */
    getObservedStateStorage(record) {
        // Add entry for current target if not already present.
        if (!this.lastObservedState.has(record.target)) {
            this.lastObservedState.set(record.target, {
                attributes: new Map(),
                classList: new Map(),
                characterData: new Map(),
            });
        }
        const stateMap = this.lastObservedState.get(record.target)[record.type];
        switch (record.type) {
            case "attributes":
                return { stateMap, key: record.attributeName };
            case "classList":
                return { stateMap, key: record.className };
            case "characterData":
                return { stateMap, key: "textContent" };
            default:
                throw new Error(`Unsupported mutation type: ${record.type}`);
        }
    }

    /**
     * This function, alongside @see storeOldValue, ensures mutation records
     * have the correct historical "oldValue" by checking against the last
     * observed state.
     *
     * When the observer is enabled, it updates a record's `oldValue` with the last
     * observed state, and removes the entry to prevent reuse. Without removing
     * the entry, the same historical value might be incorrectly applied to
     * future mutation records targeting the same attribute/class of the same
     * element, which would create incorrect history mutations.
     *
     * @param {NativeMutationRecordAttributes|NativeMutationRecordClassList|NativeMutationRecordCharacterData} record
     * @returns {NativeMutationRecordAttributes|NativeMutationRecordClassList|NativeMutationRecordCharacterData}
     */
    updateOldValue(record) {
        const { stateMap, key } = this.getObservedStateStorage(record);
        if (!stateMap.has(key)) {
            return record;
        }
        const lastObservedValue = stateMap.get(key);
        // Remove entry, so it won't be used again.
        stateMap.delete(key);
        return { ...record, oldValue: lastObservedValue };
    }

    // Staging stuff

    /**
     * Set the serialized selection of the currentChanges.
     *
     * This method is used to save a serialized selection in the currentChanges.
     * It will be necessary if the commit is reverted at some point because we
     * need to set the selection to where it was before any mutation was made.
     *
     * It means that we should not call this method in the middle of mutations
     * because if a selection is set onto a node that is edited/added/removed
     * within the same commit, it might become impossible to set the selection
     * when reverting the commit.
     */
    stageSelection() {
        this.stageFocus();
        const selection = this.dependencies.selection.getEditableSelection();
        if (this.hasStagedMutations()) {
            console.warn(
                `should not have any "characterData", "remove" or "add" mutations in current changes when you update the selection`
            );
            return;
        }
        this.updateLocal("selection", this.serializeSelection(selection));
    }

    /**
     * Set the serialized focus of the currentChanges.
     */
    stageFocus() {
        let activeElement = this.document.activeElement;
        if (activeElement.contains(this.editable)) {
            activeElement = this.editable;
        }
        if (this.editable.contains(activeElement)) {
            this.updateLocal("activeElementId", this.setNodeId(activeElement));
        }
    }

    // Custom mutations

    applyCustomMutation({ apply, revert }) {
        apply();
        this.addCustomMutation({ apply, revert });
    }

    addCustomMutation({ apply, revert }) {
        const customMutation = {
            type: "custom",
            // Note AGE: this definitely fails in collaborative since it's not
            // serializable. Do we need it in collaborative?
            apply: () => {
                apply();
                this.addCustomMutation({ apply, revert });
            },
            revert: () => {
                revert();
                this.addCustomMutation({ apply: revert, revert: apply });
            },
        };
        this.currentChanges.mutations.push(customMutation);
    }

    // Preview stuff

    /**
     * Returns a function that can be later called to revert history to the
     * current state.
     * @returns {Function}
     */
    makeSavePoint() {
        this.handleObserverRecords();
        const draftMutations = [...this.currentChanges.mutations];
        // TODO ABD TODO @phoenix: selection may become obsolete, it should evolve with mutations.
        const selectionToRestore = this.dependencies.selection.preserveSelection();

        // Preserve any current data not handled by this plugin for a later commit.
        const dataToPreserve = { ...this.currentChanges };
        Object.keys(dataToPreserve).forEach(
            (key) => DOM_MUTATION_COMMIT_DATA_KEYS.includes(key) && delete dataToPreserve[key]
        );

        const step = this.dependencies.history.getHistorySteps().at(-1);
        let hasBeenRestored = false;
        return () => {
            if (hasBeenRestored) {
                return;
            }
            hasBeenRestored = true;
            // AGE: start oldHistory.restoreToStep
            this.discardDraft();
            let lastRevertedChanges = { ...this.currentChanges };
            const commitsToRestore = this.dependencies.history.getCommitsUntil(step.id);
            const irreversibleCommits = [];
            for (const commitToRestore of commitsToRestore) {
                this.revertMutations(commitToRestore.data.mutations, { ensureNewMutations: true });
                // Process (filter, handle and stage) mutations so that the
                // attribute comparison for the state change is done with the
                // intermediate attribute value and not with the final value in the
                // DOM after all commits were reverted then applied again.
                this.processNewRecords(this.observer.takeRecords());
                if (commitToRestore.discard) {
                    commitToRestore.discard();
                    lastRevertedChanges = commitToRestore.data;
                } else {
                    irreversibleCommits.unshift(commitToRestore);
                }
            }
            // Re-apply every non reversible commit (typically collaborators commits).
            for (const irreversibleCommit of irreversibleCommits) {
                this.applyMutations(irreversibleCommit.data.mutations, {
                    ensureNewMutations: true,
                });
                this.processNewRecords(this.observer.takeRecords());
            }
            // TODO ABD TODO @phoenix: review selections, this selection could be obsolete
            // depending on the non-reversible commits that were applied.
            this.setSerializedSelection(lastRevertedChanges.selection);
            // Register resulting mutations as a new "restore" commit (prevent undo).
            this.dispatchContentUpdated();
            this.commit("restore");
            // AGE: end oldHistory.restoreToStep

            // Apply draft mutations to recover the same currentStep state
            // as before.
            this.applyMutations(draftMutations, { ensureNewMutations: true });
            this.handleObserverRecords();
            // TODO ABD TODO @phoenix: evaluate if the selection is not restorable at the desired position
            selectionToRestore.restore();
            Object.entries(dataToPreserve).forEach(([key, value]) => {
                // TODO AGE: If I remove the warning in `update`, I could
                // actually skip the check when making `dataToPreserve`.
                this.update(key, value);
            });
            this.dispatchTo("restore_savepoint_handlers");
        };
    }

    /**
     * Creates a set of functions to preview, apply, and revert an operation.
     * @param {Function} operation
     * @returns {PreviewableOperation}
     */
    makePreviewableOperation(operation) {
        let revertOperation = () => {};

        return {
            preview: (...args) => {
                revertOperation();
                revertOperation = this.makeSavePoint();
                this.isPreviewing = true;
                this.stageSelection();
                operation(...args);
                // todo: We should not add a step on preview as it would send
                // unnecessary steps in collaboration and let the other peer see
                // what we preview.
                //
                // The operation should be similar than in the 'commit'
                // (normalize etc...) hence the 'addStep' (but we need to remove
                // it for the collaboration).
                this.commit();
            },
            commit: (...args) => {
                revertOperation();
                this.isPreviewing = false;
                operation(...args);
                this.commit();
            },
            revert: () => {
                revertOperation();
                revertOperation = () => {};
                this.isPreviewing = false;
            },
        };
    }

    /**
     * Creates a set of functions to preview, apply, and revert an async operation.
     * @param {Function} operation
     * @returns {PreviewableOperation}
     */
    makePreviewableAsyncOperation(operation) {
        let revertOperation = async () => {};

        return {
            preview: async (...args) => {
                await revertOperation();
                const { promise, resolve } = Promise.withResolvers();
                const revertSavePoint = this.makeSavePoint();
                revertOperation = async () => {
                    await promise;
                    revertSavePoint();
                };
                this.isPreviewing = true;
                try {
                    await operation(...args);
                } catch (error) {
                    revertSavePoint();
                    throw error;
                } finally {
                    resolve();
                }
                if (this.isDestroyed) {
                    return;
                }
                // todo: We should not add a step on preview as it would send
                // unnecessary steps in collaboration and let the other peer see
                // what we preview.
                //
                // The operation should be similar than in the 'commit'
                // (normalize etc...) hence the 'addStep' (but we need to remove
                // it for the collaboration).
                this.commit();
            },
            commit: async (...args) => {
                await revertOperation();
                this.isPreviewing = false;
                const revertSavePoint = this.makeSavePoint();
                try {
                    await operation(...args);
                } catch (error) {
                    revertSavePoint();
                    throw error;
                }
                if (this.isDestroyed) {
                    return;
                }
                this.commit();
            },
            revert: async () => {
                await revertOperation();
                revertOperation = () => {};
                this.isPreviewing = false;
            },
        };
    }

    getIsPreviewing() {
        return !!this.isPreviewing;
    }

    /**
     * Returns the deepest common ancestor element of the given mutations.
     * @param {(EditorMutation)[]} mutations - The array of mutations.
     * @returns {HTMLElement|null} - The common ancestor element.
     */
    getMutationsRoot(mutations) {
        const nodes = mutations
            .map((m) => this.getNodeById(m.parentNodeId || m.nodeId))
            .filter((node) => this.editable.contains(node));
        let commonAncestor = getCommonAncestor(nodes, this.editable);
        if (commonAncestor?.nodeType === Node.TEXT_NODE) {
            commonAncestor = commonAncestor.parentElement;
        }
        return commonAncestor;
    }

    /**
     * @returns { CommitId  }
     */
    generateId() {
        // No need for secure random number.
        return Math.floor(Math.random() * Math.pow(2, 52)).toString();
    }
}
