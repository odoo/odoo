import { Plugin } from "../plugin";
import { childNodes, descendants, getCommonAncestor } from "../utils/dom_traversal";

/**
 * @typedef { import("./selection_plugin").EditorSelection } EditorSelection
 *
 * @typedef { Object } SerializedSelection
 * @property { string } anchorNodeId
 * @property { number } anchorOffset
 * @property { string } focusNodeId
 * @property { number } focusOffset
 *
 * @typedef { Object } SerializedNode
 * @property { number } nodeType
 * @property { string } nodeId
 * @property { string } textValue
 * @property { string } tagName
 * @property { SerializedNode[] } children
 * @property { Record<string, string> } attributes
 *
 * @typedef { Object } HistoryStep
 * @property { string } id
 * @property { SerializedSelection } selection
 * @property { HistoryMutation[] } mutations
 * @property { string } previousStepId
 *
 * @typedef { Object } HistoryMutationCharacterData
 * @property { "characterData" } type
 * // todo change id to nodeId
 * @property { string } id
 * // todo change text to textValue
 * @property { string } text
 * // todo change text to textOldValue
 * @property { string } oldValue
 *
 * @typedef { Object } HistoryMutationAttributes
 * @property { "attributes" } type
 * // todo change id to nodeId
 * @property { string } id
 * @property { string } attributeName
 * // todo change value to attributeValue
 * @property { string } value
 * // todo change oldValue to attributeOldValue
 * @property { string } oldValue
 *
 * @typedef { Object } HistoryMutationAdd
 * @property { "add" } type
 * // todo change id to nodeId
 * @property { string } id
 * @property { string } node
 * // todo change prepend to prependNodeId
 * @property { string } prepend
 * // todo change append to appendNodeId
 * @property { string } append
 * // todo change before to beforeNodeId
 * @property { string } before
 * // todo change after to afterNodeId
 * @property { string } after
 *
 * @typedef { Object } HistoryMutationRemove
 * @property { "remove" } type
 * // todo change id to nodeId
 * @property { string } id
 * // todo change parentId to parentNodeId
 * @property { string } parentId
 * @property { Node } node
 * // todo change nextId to nextNodeId
 * @property { string } nextId
 * // todo change previousId to previousNodeId
 * @property { string } previousId
 *
 * @typedef { HistoryMutationCharacterData | HistoryMutationAttributes | HistoryMutationAdd | HistoryMutationRemove } HistoryMutation
 *
 * @typedef { Object } PreviewableOperation
 * @property { Function } apply
 * @property { Function } preview
 * @property { Function } revert
 */

export class HistoryPlugin extends Plugin {
    static name = "history";
    static dependencies = ["dom", "selection", "sanitize"];
    static shared = [
        "reset",
        "canUndo",
        "canRedo",
        "makeSavePoint",
        "makePreviewableOperation",
        "makeSnapshotStep",
        "disableObserver",
        "enableObserver",
        "addExternalStep",
        "getHistorySteps",
        "historyResetFromSteps",
        "serializeSelection",
        "getNodeById",
    ];
    resources = {
        shortcuts: [
            { hotkey: "control+z", command: "HISTORY_UNDO" },
            { hotkey: "control+y", command: "HISTORY_REDO" },
            { hotkey: "control+shift+z", command: "HISTORY_REDO" },
        ],
    };

    setup() {
        this.mutationFilteredClasses = new Set(this.getResource("mutation_filtered_classes"));
        this._onKeyupResetContenteditableNodes = [];
        this.addDomListener(this.document, "beforeinput", this._onDocumentBeforeInput.bind(this));
        this.addDomListener(this.document, "input", this._onDocumentInput.bind(this));
        this.addDomListener(this.editable, "pointerup", () => {
            this.stageSelection();
        });
        this.observer = new MutationObserver(this.handleNewRecords.bind(this));
        this._cleanups.push(() => this.observer.disconnect());
        this.clean();
    }
    handleCommand(command, payload) {
        switch (command) {
            case "START_EDITION":
                this.enableObserver();
                this.reset(this.config.content);
                break;
            case "HISTORY_UNDO":
                this.undo();
                break;
            case "HISTORY_REDO":
                this.redo();
                break;
            case "ADD_STEP":
                this.addStep();
                break;
            case "HISTORY_STAGE_SELECTION":
                this.stageSelection();
                break;
        }
    }

    clean() {
        this.handleObserverRecords();
        /** @type { HistoryStep[] } */
        this.steps = [];
        /** @type { HistoryStep } */
        this.currentStep = this.processHistoryStep({
            selection: {},
            mutations: [],
            id: this.generateId(),
            previousStepId: undefined,
        });
        /** @type { Map<string, "consumed"|"undo"|"redo"> } */
        this.stepsStates = new Map();
        this.nodeToIdMap = new WeakMap();
        this.idToNodeMap = new Map();
        this.setNodeId(this.editable);
        this.dispatch("HISTORY_CLEAN");
    }
    getNodeById(id) {
        return this.idToNodeMap.get(id);
    }
    /**
     * Reset the history.
     *
     * @param { string } content
     */
    reset(content) {
        this.clean();
        this.stageSelection();
        this.steps.push(this.makeSnapshotStep());
        this.dispatch("HISTORY_RESET", { content });
    }
    /**
     * @param { HistoryStep[] } steps
     */
    historyResetFromSteps(steps) {
        this.disableObserver();
        this.editable.replaceChildren();
        this.clean();
        this.stageSelection();
        for (const step of steps) {
            this.applyMutations(step.mutations);
        }
        this.steps = steps;
        // todo: to test
        this.getResource("historyResetFromSteps").forEach((cb) => cb());

        this.enableObserver();
        this.dispatch("HISTORY_RESET_FROM_STEPS");
    }
    makeSnapshotStep() {
        return {
            selection: {
                anchorNode: undefined,
                anchorOffset: undefined,
                focusNode: undefined,
                focusOffset: undefined,
            },
            mutations: childNodes(this.editable).map((node) => ({
                type: "add",
                append: "root",
                id: this.nodeToIdMap.get(node),
                node: this.serializeNode(node),
            })),
            id: this.steps[this.steps.length - 1]?.id || this.generateId(),
            previousStepId: undefined,
        };
    }

    getHistorySteps() {
        return this.steps;
    }
    /**
     * @param { HistoryStep } step
     */
    processHistoryStep(step) {
        for (const fn of this.getResource("process_history_step")) {
            step = fn(step);
        }
        return step;
    }

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
    disableObserver() {
        // @todo @phoenix do we still want to unobserve sometimes?
        this.handleObserverRecords();
        this.observer.disconnect();
    }

    handleObserverRecords() {
        this.handleNewRecords(this.observer.takeRecords());
    }

    /**
     * @param { MutationRecord[] } records
     * @returns { MutationRecord[] } processed records
     */
    processNewRecords(records) {
        this.setIdOnRecords(records);
        records = this.filterMutationRecords(records);
        if (!records.length) {
            return [];
        }
        this.getResource("handleNewRecords").forEach((cb) => cb(records));
        this.stageRecords(records);
        return records;
    }

    dispatchContentUpdated() {
        if (!this.currentStep?.mutations?.length) {
            return;
        }
        // @todo @phoenix remove this?
        // @todo @phoenix this includes previous mutations that were already
        // stored in the current step. Ideally, it should only include the new ones.
        const root = this.getMutationsRoot(this.currentStep.mutations);
        if (!root) {
            return;
        }
        this.dispatch("CONTENT_UPDATED", {
            root,
        });
    }

    /**
     * @param { MutationRecord[] } records
     */
    handleNewRecords(records) {
        if (this.processNewRecords(records).length) {
            this.dispatchContentUpdated();
        }
    }

    /**
     * @param { MutationRecord[] } records
     */
    setIdOnRecords(records) {
        for (const record of records) {
            if (record.type === "childList" && record.addedNodes.length) {
                for (const node of record.addedNodes) {
                    this.setNodeId(node);
                }
            }
        }
    }
    /**
     * @param { MutationRecord[] } records
     */
    filterMutationRecords(records) {
        this.dispatch("BEFORE_FILTERING_MUTATION_RECORDS", {
            records,
        });
        for (const callback of this.getResource("is_mutation_record_savable")) {
            records = records.filter(callback);
        }

        // Save the first attribute in a cache to compare only the first
        // attribute record of node to its latest state.
        const attributeCache = new Map();
        const filteredRecords = [];

        for (const record of records) {
            if (record.type === "attributes") {
                // Skip the attributes change on the dom.
                if (record.target === this.editable) {
                    continue;
                }
                if (record.attributeName === "contenteditable") {
                    continue;
                }
                // @todo @phoenix test attributeCache
                attributeCache.set(record.target, attributeCache.get(record.target) || {});
                // @todo @phoenix add test for mutationFilteredClasses.
                if (record.attributeName === "class") {
                    const classBefore = (record.oldValue && record.oldValue.split(" ")) || [];
                    const classAfter =
                        (record.target.className &&
                            record.target.className.split &&
                            record.target.className.split(" ")) ||
                        [];
                    const excludedClasses = [];
                    for (const klass of classBefore) {
                        if (!classAfter.includes(klass)) {
                            excludedClasses.push(klass);
                        }
                    }
                    for (const klass of classAfter) {
                        if (!classBefore.includes(klass)) {
                            excludedClasses.push(klass);
                        }
                    }
                    if (
                        excludedClasses.length &&
                        excludedClasses.every((c) => this.mutationFilteredClasses.has(c))
                    ) {
                        continue;
                    }
                }
                if (
                    typeof attributeCache.get(record.target)[record.attributeName] === "undefined"
                ) {
                    const oldValue = record.oldValue === undefined ? null : record.oldValue;
                    attributeCache.get(record.target)[record.attributeName] =
                        oldValue !== record.target.getAttribute(record.attributeName);
                }
                if (!attributeCache.get(record.target)[record.attributeName]) {
                    continue;
                }
            }
            filteredRecords.push(record);
        }
        // @todo @phoenix allow an option to filter mutation records.
        return filteredRecords;
    }

    /**
     * Set the serialized selection of the currentStep.
     *
     * This method is used to save a serialized selection in the currentStep.
     * It will be necessary if the step is reverted at some point because we need
     * to set the selection to where it was before any mutation was made.
     *
     * It means that we should not call this method in the middle of mutations
     * because if a selection is set onto a node that is edited/added/removed
     * within the same step, it might become impossible to set the selection
     * when reverting the step.
     */
    stageSelection() {
        const selection = this.shared.getEditableSelection();
        if (
            this.currentStep.mutations.find((m) =>
                ["characterData", "remove", "add"].includes(m.type)
            )
        ) {
            console.warn(
                `should not have any "characterData", "remove" or "add" mutations in current step when you update the selection`
            );
            return;
        }
        this.currentStep.selection = this.serializeSelection(selection);
    }
    /**
     * @param { MutationRecord[] } records
     */
    stageRecords(records) {
        // @todo @phoenix test this feature.
        // There is a case where node A is added and node B is a descendant of
        // node A where node B was not in the observed tree) then node B is
        // added into another node. In that case, we need to keep track of node
        // B so when serializing node A, we strip node B from the node A tree to
        // avoid the duplication of node A.
        const mutatedNodes = new Set();
        for (const record of records) {
            if (record.type === "childList") {
                for (const node of record.addedNodes) {
                    const id = this.setNodeId(node);
                    mutatedNodes.add(id);
                }
                for (const node of record.removedNodes) {
                    const id = this.setNodeId(node);
                    mutatedNodes.delete(id);
                }
            }
        }
        for (const record of records) {
            switch (record.type) {
                case "characterData": {
                    this.currentStep.mutations.push({
                        type: "characterData",
                        id: this.nodeToIdMap.get(record.target),
                        text: record.target.textContent,
                        oldValue: record.oldValue,
                    });
                    break;
                }
                case "attributes": {
                    this.currentStep.mutations.push({
                        type: "attributes",
                        id: this.nodeToIdMap.get(record.target),
                        attributeName: record.attributeName,
                        value: record.target.getAttribute(record.attributeName),
                        oldValue: record.oldValue,
                    });
                    for (const cb of this.getResource("on_change_attribute")) {
                        cb({
                            target: record.target,
                            attributeName: record.attributeName,
                            oldValue: record.oldValue,
                            value: record.target.getAttribute(record.attributeName),
                        });
                    }
                    break;
                }
                case "childList": {
                    record.addedNodes.forEach((added) => {
                        const mutation = {
                            type: "add",
                        };
                        if (!record.nextSibling && this.nodeToIdMap.get(record.target)) {
                            mutation.append = this.nodeToIdMap.get(record.target);
                        } else if (record.nextSibling && this.nodeToIdMap.get(record.nextSibling)) {
                            mutation.before = this.nodeToIdMap.get(record.nextSibling);
                        } else if (!record.previousSibling && this.nodeToIdMap.get(record.target)) {
                            mutation.prepend = this.nodeToIdMap.get(record.target);
                        } else if (
                            record.previousSibling &&
                            this.nodeToIdMap.get(record.previousSibling)
                        ) {
                            mutation.after = this.nodeToIdMap.get(record.previousSibling);
                        } else {
                            return false;
                        }
                        mutation.id = this.nodeToIdMap.get(added);
                        mutation.node = this.serializeNode(added, mutatedNodes);
                        this.currentStep.mutations.push(mutation);
                    });
                    record.removedNodes.forEach((removed) => {
                        this.currentStep.mutations.push({
                            type: "remove",
                            id: this.nodeToIdMap.get(removed),
                            parentId: this.nodeToIdMap.get(record.target),
                            node: this.serializeNode(removed),
                            nextId: record.nextSibling
                                ? this.nodeToIdMap.get(record.nextSibling)
                                : undefined,
                            previousId: record.previousSibling
                                ? this.nodeToIdMap.get(record.previousSibling)
                                : undefined,
                        });
                    });
                    break;
                }
            }
        }
    }

    /**
     * @param { Node } node
     */
    setNodeId(node) {
        let id = this.nodeToIdMap.get(node);
        if (!id) {
            id = node === this.editable ? "root" : this.generateId();
            this.nodeToIdMap.set(node, id);
            this.idToNodeMap.set(id, node);
            node = node.firstChild;
            while (node) {
                this.setNodeId(node);
                node = node.nextSibling;
            }
        }
        return id;
    }
    generateId() {
        // No need for secure random number.
        return Math.floor(Math.random() * Math.pow(2, 52)).toString();
    }

    /**
     * @param { Object } [params]
     * @param { "consumed"|"undo"|"redo" } [params.stepState]
     */
    addStep({ stepState } = {}) {
        // @todo @phoenix should we allow to pause the making of a step?
        // if (!this.stepsActive) {
        //     return;
        // }
        // @todo @phoenix link zws plugin
        // this._resetLinkZws();
        // @todo @phoenix sanitize plugin
        // this.sanitize();

        this.handleObserverRecords();
        const currentStep = this.currentStep;
        if (!currentStep.mutations.length) {
            return false;
        }
        const stepCommonAncestor = this.getMutationsRoot(currentStep.mutations) || this.editable;
        this.dispatch("NORMALIZE", { node: stepCommonAncestor });
        this.handleObserverRecords();

        currentStep.previousStepId = this.steps.at(-1)?.id;

        this.steps.push(currentStep);
        // @todo @phoenix add this in the linkzws plugin.
        // this._setLinkZws();
        this.currentStep = this.processHistoryStep({
            id: this.generateId(),
            selection: {},
            mutations: [],
            previousStepId: undefined,
        });
        // Set the state of the step here.
        // That way, the state of undo and redo is truly accessible
        // when executing the onChange callback.
        // It is useful for external components if they execute shared.can[Undo|Redo]
        if (stepState) {
            this.stepsStates.set(currentStep.id, stepState);
        }
        this.stageSelection();
        this.dispatch("STEP_ADDED", {
            step: currentStep,
            stepCommonAncestor,
        });
        this.config.onChange?.();
        return currentStep;
    }
    canUndo() {
        return this.getNextUndoIndex() > 0;
    }
    canRedo() {
        return this.getNextRedoIndex() > 0;
    }
    undo() {
        if (this.steps.length === 1) {
            return;
        }
        this.handleObserverRecords();
        // The last step is considered an uncommited draft so always revert it.
        const lastStep = this.currentStep;
        this.revertMutations(lastStep.mutations);
        // Discard mutations generated by the revert.
        this.observer.takeRecords();
        // Clean the last step otherwise if no other step is created after, the
        // mutations of the revert itself will be added to the same step and
        // grow exponentially at each undo.
        lastStep.mutations = [];

        const pos = this.getNextUndoIndex();
        if (pos > 0) {
            // Consider the position consumed.
            this.stepsStates.set(this.steps[pos].id, "consumed");
            this.revertMutations(this.steps[pos].mutations, { forNewStep: true });
            this.setSerializedSelection(this.steps[pos].selection);
            this.addStep({ stepState: "undo" });
            // Consider the last position of the history as an undo.
        }
    }
    redo() {
        this.handleObserverRecords();
        // Current step is considered an uncommitted draft, so revert it,
        // otherwise a redo would not be possible.
        this.revertMutations(this.currentStep.mutations);
        // Discard mutations generated by the revert.
        this.observer.takeRecords();
        // At this point, _currentStep.mutations contains the current step's
        // mutations plus the ones that revert it, with net effect zero.
        this.currentStep.mutations = [];

        const pos = this.getNextRedoIndex();
        if (pos > 0) {
            this.stepsStates.set(this.steps[pos].id, "consumed");
            this.revertMutations(this.steps[pos].mutations, { forNewStep: true });
            this.setSerializedSelection(this.steps[pos].selection);
            this.addStep({ stepState: "redo" });
        }
    }
    /**
     * @param { SerializedSelection } selection
     */
    setSerializedSelection(selection) {
        if (!selection.anchorNodeId) {
            return;
        }
        const anchorNode = this.idToNodeMap.get(selection.anchorNodeId);
        if (!anchorNode) {
            return;
        }
        const newSelection = {
            anchorNode,
            anchorOffset: selection.anchorOffset,
        };
        const focusNode = this.idToNodeMap.get(selection.focusNodeId);
        if (focusNode) {
            newSelection.focusNode = focusNode;
            newSelection.focusOffset = selection.focusOffset;
        }
        this.shared.setSelection(newSelection, { normalize: false });
        // @todo @phoenix add this in the selection or table plugin.
        // // If a table must be selected, ensure it's in the same tick.
        // this._handleSelectionInTable();
    }
    /**
     * Get the step index in the history to undo.
     * Return -1 if no undo index can be found.
     */
    getNextUndoIndex() {
        // Go back to first step that can be undone ("redo" or undefined).
        for (let index = this.steps.length - 1; index >= 0; index--) {
            if (this.isReversibleStep(index)) {
                const state = this.stepsStates.get(this.steps[index].id);
                if (state === "redo" || !state) {
                    return index;
                }
            }
        }
        // There is no steps left to be undone, return an index that does not
        // point to any step
        return -1;
    }
    /**
     * Meant to be overriden.
     *
     * @param { number } index
     */
    isReversibleStep(index) {
        for (const cb of this.getResource("is_reversible_step")) {
            const result = cb(index);
            if (typeof result !== "undefined") {
                return result;
            }
        }
        return Boolean(this.steps[index]);
    }
    /**
     * Get the step index in the history to redo.
     * Return -1 if no redo index can be found.
     */
    getNextRedoIndex() {
        // We cannot redo more than what is consumed.
        // Check if we have no more "consumed" than "redo" until we get to an
        // "undo"
        let totalConsumed = 0;
        for (let index = this.steps.length - 1; index >= 0; index--) {
            if (this.isReversibleStep(index)) {
                const state = this.stepsStates.get(this.steps[index].id);
                switch (state) {
                    case "undo":
                        return totalConsumed <= 0 ? index : -1;
                    case "redo":
                        totalConsumed -= 1;
                        break;
                    case "consumed":
                        totalConsumed += 1;
                        break;
                    default:
                        return -1;
                }
            }
        }
        return -1;
    }
    /**
     * Insert a step in the history.
     *
     * @param { HistoryStep } newStep
     * @param { number } index
     */
    addExternalStep(newStep, index) {
        // The last step is an uncommited draft, revert it first
        this.revertMutations(this.currentStep.mutations);

        const stepsAfterNewStep = this.steps.slice(index);

        for (const stepToRevert of stepsAfterNewStep.slice().reverse()) {
            this.revertMutations(stepToRevert.mutations);
        }
        this.applyMutations(newStep.mutations);
        this.dispatch("NORMALIZE", {
            node: this.getMutationsRoot(newStep.mutations) || this.editable,
        });
        this.steps.splice(index, 0, newStep);
        for (const stepToApply of stepsAfterNewStep) {
            this.applyMutations(stepToApply.mutations);
        }
        // Reapply the uncommited draft, since this is not an operation which should cancel it
        this.applyMutations(this.currentStep.mutations);
    }
    /**
     * @param { HistoryMutation[] } mutations
     * @param { Object } options
     * @param { boolean } options.forNewStep whether the mutations will be used
     *        to create a new step
     */
    applyMutations(mutations, { forNewStep = false } = {}) {
        for (const mutation of mutations) {
            switch (mutation.type) {
                case "characterData": {
                    const node = this.idToNodeMap.get(mutation.id);
                    if (node) {
                        node.textContent = mutation.text;
                    }
                    break;
                }
                case "attributes": {
                    const node = this.idToNodeMap.get(mutation.id);
                    if (node) {
                        let value = this.getAttributeValue(mutation.attributeName, mutation.value);
                        for (const cb of this.getResource("on_change_attribute")) {
                            value =
                                cb(
                                    {
                                        target: node,
                                        attributeName: mutation.attributeName,
                                        oldValue: mutation.oldValue,
                                        value,
                                    },
                                    { forNewStep }
                                ) || value;
                        }
                        this.setAttribute(node, mutation.attributeName, value);
                    }
                    break;
                }
                case "remove": {
                    const toremove = this.idToNodeMap.get(mutation.id);
                    if (toremove) {
                        toremove.remove();
                    }
                    break;
                }
                case "add": {
                    const node =
                        this.idToNodeMap.get(mutation.id) || this.unserializeNode(mutation.node);
                    if (!node) {
                        continue;
                    }

                    this.setNodeId(node);

                    if (mutation.append && this.idToNodeMap.get(mutation.append)) {
                        this.idToNodeMap.get(mutation.append).append(node);
                    } else if (mutation.before && this.idToNodeMap.get(mutation.before)) {
                        this.idToNodeMap.get(mutation.before).before(node);
                    } else if (mutation.after && this.idToNodeMap.get(mutation.after)) {
                        this.idToNodeMap.get(mutation.after).after(node);
                    } else {
                        continue;
                    }
                    break;
                }
            }
        }
    }
    /**
     * @param { HistoryMutation[] } mutations
     * @param { Object } options
     * @param { boolean } options.forNewStep whether the mutations will be used
     *        to create a new step
     */
    revertMutations(mutations, { forNewStep = false } = {}) {
        for (const mutation of mutations.toReversed()) {
            switch (mutation.type) {
                case "characterData": {
                    const node = this.idToNodeMap.get(mutation.id);
                    if (node) {
                        node.textContent = mutation.oldValue;
                    }
                    break;
                }
                case "attributes": {
                    const node = this.idToNodeMap.get(mutation.id);
                    if (node) {
                        let value = this.getAttributeValue(
                            mutation.attributeName,
                            mutation.oldValue
                        );
                        for (const cb of this.getResource("on_change_attribute")) {
                            value =
                                cb(
                                    {
                                        target: node,
                                        attributeName: mutation.attributeName,
                                        oldValue: mutation.value,
                                        value,
                                        reverse: true,
                                    },
                                    { forNewStep }
                                ) || value;
                        }
                        this.setAttribute(node, mutation.attributeName, value);
                    }
                    break;
                }
                case "remove": {
                    let nodeToRemove = this.idToNodeMap.get(mutation.id);
                    if (!nodeToRemove) {
                        nodeToRemove = this.unserializeNode(mutation.node);
                        if (!nodeToRemove) {
                            continue;
                        }
                    }
                    if (mutation.nextId && this.idToNodeMap.get(mutation.nextId)?.isConnected) {
                        const node = this.idToNodeMap.get(mutation.nextId);
                        node && node.before(nodeToRemove);
                    } else if (
                        mutation.previousId &&
                        this.idToNodeMap.get(mutation.previousId)?.isConnected
                    ) {
                        const node = this.idToNodeMap.get(mutation.previousId);
                        node && node.after(nodeToRemove);
                    } else {
                        const node = this.idToNodeMap.get(mutation.parentId);
                        node && node.append(nodeToRemove);
                    }
                    break;
                }
                case "add": {
                    const node = this.idToNodeMap.get(mutation.id);
                    if (node) {
                        node.remove();
                    }
                }
            }
        }
    }

    /**
     * Serialize an editor selection.
     * @param { EditorSelection } selection
     * @returns { SerializedSelection }
     */
    serializeSelection(selection) {
        return {
            anchorNodeId: this.nodeToIdMap.get(selection.anchorNode),
            anchorOffset: selection.anchorOffset,
            focusNodeId: this.nodeToIdMap.get(selection.focusNode),
            focusOffset: selection.focusOffset,
        };
    }
    /**
     * Returns the deepest common ancestor element of the given mutations.
     * @param {HistoryMutation[]} - The array of mutations.
     * @returns {HTMLElement|null} - The common ancestor element.
     */
    getMutationsRoot(mutations) {
        const nodes = mutations
            .map((m) => this.idToNodeMap.get(m.parentId || m.id))
            .filter((node) => this.editable.contains(node));
        let commonAncestor = getCommonAncestor(nodes, this.editable);
        if (commonAncestor?.nodeType === Node.TEXT_NODE) {
            commonAncestor = commonAncestor.parentElement;
        }
        return commonAncestor;
    }
    /**
     * Returns a function that can be later called to revert history to the
     * current state.
     * @returns {Function}
     */
    makeSavePoint() {
        this.handleObserverRecords();
        const draftMutations = this.currentStep.mutations.slice();
        const step = this.steps.at(-1);
        let applied = false;
        // TODO ABD TODO @phoenix: selection may become obsolete, it should evolve with mutations.
        const selectionToRestore = this.shared.preserveSelection();
        return () => {
            if (applied) {
                return;
            }
            applied = true;
            const stepIndex = this.steps.findLastIndex((item) => item === step);
            this.revertStepsUntil(stepIndex);
            // Apply draft mutations to recover the same currentStep state
            // as before.
            this.applyMutations(draftMutations, { forNewStep: true });
            this.handleObserverRecords();
            // TODO ABD TODO @phoenix: evaluate if the selection is not restorable at the desired position
            selectionToRestore.restore();
            this.dispatch("RESTORE_SAVEPOINT");
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
                operation(...args);
            },
            commit: (...args) => {
                revertOperation();
                operation(...args);
                this.addStep();
            },
            revert: () => {
                revertOperation();
            },
        };
    }
    /**
     * Discard the current draft, and, if necessary, consume and revert
     * reversible steps until the specified step index, and ensure that
     * irreversible steps are maintained. This will add a new consumed step.
     *
     * @param {Number} stepIndex
     */
    revertStepsUntil(stepIndex) {
        // Discard current draft.
        this.handleObserverRecords();
        this.revertMutations(this.currentStep.mutations);
        this.observer.takeRecords();
        this.currentStep.mutations = [];
        let lastRevertedStep = this.currentStep;

        if (stepIndex === this.steps.length - 1) {
            return;
        }
        // Revert all mutations until stepIndex, and consume all reversible
        // steps in the process (typically current peer steps).
        for (let i = this.steps.length - 1; i > stepIndex; i--) {
            const currentStep = this.steps[i];
            this.revertMutations(currentStep.mutations, { forNewStep: true });
            // Process (filter, handle and stage) mutations so that the
            // attribute comparison for the state change is done with the
            // intermediate attribute value and not with the final value in the
            // DOM after all steps were reverted then applied again.
            this.processNewRecords(this.observer.takeRecords());
            if (this.isReversibleStep(i)) {
                this.stepsStates.set(currentStep.id, "consumed");
                lastRevertedStep = currentStep;
            }
        }
        // Re-apply every non reversible steps (typically collaborators steps).
        for (let i = stepIndex + 1; i < this.steps.length; i++) {
            const currentStep = this.steps[i];
            if (!this.isReversibleStep(i)) {
                this.applyMutations(currentStep.mutations, { forNewStep: true });
                this.processNewRecords(this.observer.takeRecords());
            }
        }
        // TODO ABD TODO @phoenix: review selections, this selection could be obsolete
        // depending on the non-reversible steps that were applied.
        this.setSerializedSelection(lastRevertedStep.selection);
        // Register resulting mutations as a new consumed step (prevent undo).
        this.dispatchContentUpdated();
        this.addStep({ stepState: "consumed" });
    }

    /**
     * @param { string } attributeName
     * @param { string } value
     */
    getAttributeValue(attributeName, value) {
        if (typeof value === "string" && attributeName === "class") {
            value = value
                .split(" ")
                .filter((c) => !this.mutationFilteredClasses.has(c))
                .join(" ");
        }
        return value;
    }
    /**
     * @param { Node } node
     * @param { string } attributeName
     * @param { string } attributeValue
     */
    setAttribute(node, attributeName, attributeValue) {
        for (const cb of this.getResource("set_attribute")) {
            const result = cb(node, attributeName, attributeValue);
            if (result) {
                return;
            }
        }
        // if attributeValue is falsy but not null, we still need to apply it
        if (attributeValue !== null) {
            node.setAttribute(attributeName, attributeValue);
        } else {
            node.removeAttribute(attributeName);
        }
    }
    /**
     * Serialize a node and its children if the collaboration is true.
     * @param { Node } node
     * @param { Set<Node> } nodesToStripFromChildren
     */
    serializeNode(node, mutatedNodes) {
        return this._serializeNode(node, mutatedNodes, this.nodeToIdMap);
    }
    /**
     * Unserialize a node and its children if the collaboration is true.
     * @param { SerializedNode } node
     * @returns { Node }
     */
    unserializeNode(node) {
        let [unserializedNode, nodeMap] = this._unserializeNode(node, this.idToNodeMap);
        const fakeNode = this.document.createElement("fake-el");
        fakeNode.appendChild(unserializedNode);
        this.shared.sanitize(fakeNode, { IN_PLACE: true });
        unserializedNode = fakeNode.firstChild;

        if (unserializedNode) {
            // Only assing id to the remaining nodes, otherwise the removed
            // nodes will still be accessible through the idToNodeMap and could
            // lead to security issues.
            for (const node of [unserializedNode, ...descendants(unserializedNode)]) {
                const id = nodeMap.get(node);
                if (id) {
                    this.nodeToIdMap.set(node, id);
                    this.idToNodeMap.set(id, node);
                }
            }
            this.setNodeId(unserializedNode);
            return unserializedNode;
        }
    }
    /**
     * Serialize a node and its children.
     * @param { Node } node
     * @param { [Set<Node>] } nodesToStripFromChildren
     * @returns { SerializedNode }
     */
    _serializeNode(node, nodesToStripFromChildren = new Set()) {
        const nodeId = this.nodeToIdMap.get(node);
        if (!nodeId) {
            return;
        }
        const result = {
            nodeType: node.nodeType,
            nodeId: nodeId,
        };
        if (node.nodeType === Node.TEXT_NODE) {
            result.textValue = node.nodeValue;
        } else if (node.nodeType === Node.ELEMENT_NODE) {
            let childrenToSerialize;
            for (const cb of this.getResource("filter_descendants_to_serialize")) {
                childrenToSerialize = cb(node);
                if (childrenToSerialize) {
                    break;
                }
            }
            if (!childrenToSerialize) {
                childrenToSerialize = childNodes(node);
            }
            result.tagName = node.tagName;
            result.children = [];
            result.attributes = {};
            for (let i = 0; i < node.attributes.length; i++) {
                result.attributes[node.attributes[i].name] = node.attributes[i].value;
            }
            for (const child of childrenToSerialize) {
                if (!nodesToStripFromChildren.has(child.nodeId)) {
                    const serializedChild = this._serializeNode(child, nodesToStripFromChildren);
                    if (serializedChild) {
                        result.children.push(serializedChild);
                    }
                }
            }
        }
        return result;
    }
    /**
     * Unserialize a node and its children.
     * @param { SerializedNode } serializedNode
     * @param { Map<Node, number> } _map
     * @returns { Node, Map<Node, number> }
     */
    _unserializeNode(serializedNode, idToNodeMap = new Map(), _map = new Map()) {
        let node = undefined;
        if (serializedNode.nodeType === Node.TEXT_NODE) {
            node = this.document.createTextNode(serializedNode.textValue);
        } else if (serializedNode.nodeType === Node.ELEMENT_NODE) {
            node = idToNodeMap.get(serializedNode.nodeId);
            if (node) {
                return [node, _map];
            }
            node = this.document.createElement(serializedNode.tagName);
            for (const key in serializedNode.attributes) {
                node.setAttribute(key, serializedNode.attributes[key]);
            }
            serializedNode.children.forEach((child) =>
                node.append(this._unserializeNode(child, idToNodeMap, _map)[0])
            );
        } else {
            console.warn("unknown node type");
        }
        _map.set(node, serializedNode.nodeId);
        return [node, _map];
    }

    _onDocumentBeforeInput(ev) {
        if (this.editable.contains(ev.targget)) {
            return;
        }
        if (["historyUndo", "historyRedo"].includes(ev.inputType)) {
            this._onKeyupResetContenteditableNodes.push(
                ...this.editable.querySelectorAll("[contenteditable=true]")
            );
            if (this.editable.getAttribute("contenteditable") === "true") {
                this._onKeyupResetContenteditableNodes.push(this.editable);
            }

            for (const node of this._onKeyupResetContenteditableNodes) {
                node.setAttribute("contenteditable", false);
            }
        }
    }

    _onDocumentInput(ev) {
        if (
            ["historyUndo", "historyRedo"].includes(ev.inputType) &&
            this._onKeyupResetContenteditableNodes.length
        ) {
            for (const node of this._onKeyupResetContenteditableNodes) {
                node.setAttribute("contenteditable", true);
            }
            this._onKeyupResetContenteditableNodes = [];
        }
    }
}
