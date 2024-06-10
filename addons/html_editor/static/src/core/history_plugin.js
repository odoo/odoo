import { Plugin } from "../plugin";
import { descendants, getCommonAncestor } from "../utils/dom_traversal";

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
    static dependencies = ["dom", "selection"];
    static shared = [
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
    static resources = () => ({
        shortcuts: [
            { hotkey: "control+z", command: "HISTORY_UNDO" },
            { hotkey: "control+y", command: "HISTORY_REDO" },
            { hotkey: "control+shift+z", command: "HISTORY_REDO" },
        ],
    });

    setup() {
        this.renderingClasses = new Set(this.resources["history_rendering_classes"]);
        this.addDomListener(this.editable, "input", () => this.addStep());
        this.addDomListener(this.editable, "pointerup", () => {
            this.stageSelection();
            this.stageNextSelection = true;
        });
        this.addDomListener(this.editable, "keydown", this.stageSelection);
        this.addDomListener(this.editable, "beforeinput", this.stageSelection);
        this.observer = new MutationObserver(this.handleNewRecords.bind(this));
        this._cleanups.push(() => this.observer.disconnect());
        this.enableObserver();
        this.reset();
    }
    handleCommand(command, payload) {
        switch (command) {
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
        /** @type { HistoryStep[] } */
        this.steps = [];
        /** @type { HistoryStep } */
        this.currentStep = this.processHistoryStep({
            selection: {
                anchorNodeId: undefined,
                anchorOffset: undefined,
                focusNodeId: undefined,
                focusOffset: undefined,
            },
            mutations: [],
            id: this.generateId(),
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
     */
    reset() {
        this.clean();
        this.steps.push(this.makeSnapshotStep());
        this.dispatch("HISTORY_RESET");
    }
    /**
     * @param { HistoryStep[] } steps
     */
    historyResetFromSteps(steps) {
        this.disableObserver();
        this.editable.replaceChildren();
        this.clean();
        for (const step of steps) {
            this.applyMutations(step.mutations);
        }
        this.snapshots = [{ step: steps[0] }];
        this.steps = steps;
        // todo: to test
        this.resources.historyResetFromSteps?.forEach((cb) => cb());

        this.enableObserver();
    }
    makeSnapshotStep() {
        return {
            selection: {
                anchorNode: undefined,
                anchorOffset: undefined,
                focusNode: undefined,
                focusOffset: undefined,
            },
            mutations: Array.from(this.editable.childNodes).map((node) => ({
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
        for (const fn of this.resources["process_history_step"] || []) {
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
     */
    handleNewRecords(records) {
        this.setIdOnRecords(records);
        records = this.filterMutationRecords(records);
        if (!records.length) {
            return;
        }
        this.resources["handleNewRecords"]?.forEach((cb) => cb(records));
        this.stageRecords(records);
        // @todo @phoenix remove this?
        // @todo @phoenix this includes previous mutations that were already
        // stored in the current step. Ideally, it should only include the new ones.
        this.dispatch("CONTENT_UPDATED", {
            root: this.getMutationsRoot(this.currentStep.mutations),
        });
    }

    /**
     * @param { MutationRecord[] } records
     */
    setIdOnRecords(records) {
        for (const record of records) {
            if (record.type === "childList") {
                this.setNodeId(record.target);
            }
        }
    }
    /**
     * @param { MutationRecord[] } records
     */
    filterMutationRecords(records) {
        for (const callback of this.resources["is_mutation_record_savable"]) {
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
                // @todo @phoenix add test for renderingClasses.
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
                        excludedClasses.every((c) => this.renderingClasses.has(c))
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
    stageSelection() {
        const selection = this.shared.getEditableSelection();
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
        }
        for (const child of node.childNodes) {
            this.setNodeId(child);
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
        this.dispatch("NORMALIZE", { node: this.getMutationsRoot(currentStep.mutations) });
        this.handleObserverRecords();

        currentStep.previousStepId = this.steps.at(-1)?.id;

        this.steps.push(currentStep);
        this.dispatch("STEP_ADDED", currentStep);
        // @todo @phoenix add this in the linkzws plugin.
        // this._setLinkZws();
        this.currentStep = this.processHistoryStep({
            id: this.generateId(),
            selection: {},
            mutations: [],
        });
        // Set the state of the step here.
        // That way, the state of undo and redo is truly accessible
        // when executing the onChange callback.
        // It is useful for external components if they execute shared.can[Undo|Redo]
        if (stepState) {
            this.stepsStates.set(currentStep.id, stepState);
        }
        this.stageSelection();
        this.config.onChange?.();
        this.dispatch("HISTORY_STEP_ADDED", currentStep);
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
        // The last step is considered an uncommited draft so always revert it.
        const lastStep = this.currentStep;
        this.revertMutations(lastStep.mutations);
        // Clean the last step otherwise if no other step is created after, the
        // mutations of the revert itself will be added to the same step and
        // grow exponentially at each undo.
        lastStep.mutations = [];

        const pos = this.getNextUndoIndex();
        if (pos > 0) {
            // Consider the position consumed.
            this.stepsStates.set(this.steps[pos].id, "consumed");
            this.revertMutations(this.steps[pos].mutations);
            this.setSerializedSelection(this.steps[pos].selection);
            this.addStep({ stepState: "undo" });
            // Consider the last position of the history as an undo.
        }
    }
    redo() {
        // Current step is considered an uncommitted draft, so revert it,
        // otherwise a redo would not be possible.
        this.revertMutations(this.currentStep.mutations);
        // At this point, _currentStep.mutations contains the current step's
        // mutations plus the ones that revert it, with net effect zero.
        this.currentStep.mutations = [];

        const pos = this.getNextRedoIndex();
        if (pos > 0) {
            this.stepsStates.set(this.steps[pos].id, "consumed");
            this.revertMutations(this.steps[pos].mutations);
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
            if (this.isRevertableStep(index)) {
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
    isRevertableStep(index) {
        for (const cb of this.resources["is_revertable_step"] || []) {
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
            if (this.isRevertableStep(index)) {
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
        const stepsAfterNewStep = this.steps.slice(index);

        for (const stepToRevert of stepsAfterNewStep.slice().reverse()) {
            this.revertMutations(stepToRevert.mutations);
        }
        this.applyMutations(newStep.mutations);
        this.steps.splice(index, 0, newStep);
        for (const stepToApply of stepsAfterNewStep) {
            this.applyMutations(stepToApply.mutations);
        }
    }
    /**
     * @param { HistoryMutation[] } mutations
     */
    applyMutations(mutations) {
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
                        const value = this.getAttributeValue(
                            mutation.attributeName,
                            mutation.value
                        );
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
     */
    revertMutations(mutations) {
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
                        const value = this.getAttributeValue(
                            mutation.attributeName,
                            mutation.oldValue
                        );
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
        const currentMutations = this.currentStep.mutations.slice();
        const currentStepMutationsUntilLength = currentMutations.length;
        const savePointIndex = this.steps.length - 1;
        let applied = false;
        const selection = this.shared.getEditableSelection();
        return () => {
            if (applied) {
                return;
            }
            applied = true;
            if (savePointIndex === this.steps.length - 1) {
                const mutationsToRevert = this.currentStep.mutations.splice(
                    currentStepMutationsUntilLength
                );
                this.revertMutations(mutationsToRevert);
                this.observer.takeRecords();
                this.shared.setSelection(selection, { normalize: false });
            } else {
                this.revertStepsUntil(savePointIndex);
                this.applyMutations(currentMutations);
            }
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
     * Reverts the history steps until the specified step index.
     * @param {number} stepIndex
     */
    revertStepsUntil(stepIndex) {
        // Discard current step's mutations
        this.revertMutations(this.currentStep.mutations);
        this.currentStep.mutations = [];

        // Revert each step that is not "consumed" until stepIndex (not inclusive).
        const stepsToRevert = this.steps
            .slice(stepIndex + 1)
            .filter((step) => this.stepsStates.get(step.id) !== "consumed");

        for (const step of stepsToRevert.toReversed()) {
            this.revertMutations(step.mutations);
            this.stepsStates.set(step.id, "consumed");
        }

        // Restore selection to last reverted step's selection.
        const lastRevertedStep = stepsToRevert[0] || this.currentStep;
        this.setSerializedSelection(lastRevertedStep.selection);

        // @phoenix @todo: should we do that here ?
        // Register resulting mutations as a new step.
        const addedStep = this.addStep();
        if (addedStep) {
            this.stepsStates.set(addedStep.id, "consumed");
        }
    }

    /**
     * @param { string } attributeName
     * @param { string } value
     */
    getAttributeValue(attributeName, value) {
        if (typeof value === "string" && attributeName === "class") {
            value = value
                .split(" ")
                .filter((c) => !this.renderingClasses.has(c))
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
        for (const cb of this.resources["set_attribute"] || []) {
            const result = cb(node, attributeName, attributeValue);
            if (result) {
                return;
            }
        }
        if (attributeValue) {
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
        let [unserializedNode, nodeMap] = this._unserializeNode(node);

        for (const cb of this.resources["unserialize_node"] || []) {
            unserializedNode = cb(unserializedNode);
        }

        if (unserializedNode) {
            // Only assing id to the remaining nodes, otherwise the removed
            // nodes will still be accessible through the idToNodeMap and could
            // lead to security issues.
            for (const node of [unserializedNode, ...descendants(unserializedNode)]) {
                const id = nodeMap.get(node);
                this.nodeToIdMap.set(node, id);
                this.idToNodeMap.set(id, node);
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
            result.tagName = node.tagName;
            result.children = [];
            result.attributes = {};
            for (let i = 0; i < node.attributes.length; i++) {
                result.attributes[node.attributes[i].name] = node.attributes[i].value;
            }
            let child = node.firstChild;
            // Don't serialize transient nodes
            // @todo @phoenix move logic into it's own transient plugin ?
            if (!["true", ""].includes(node.dataset.oeTransientContent)) {
                while (child) {
                    if (!nodesToStripFromChildren.has(child.nodeId)) {
                        const serializedChild = this._serializeNode(
                            child,
                            nodesToStripFromChildren
                        );
                        if (serializedChild) {
                            result.children.push(serializedChild);
                        }
                    }
                    child = child.nextSibling;
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
    _unserializeNode(serializedNode, _map = new Map()) {
        let node = undefined;
        if (serializedNode.nodeType === Node.TEXT_NODE) {
            node = this.document.createTextNode(serializedNode.textValue);
        } else if (serializedNode.nodeType === Node.ELEMENT_NODE) {
            node = this.document.createElement(serializedNode.tagName);
            for (const key in serializedNode.attributes) {
                node.setAttribute(key, serializedNode.attributes[key]);
            }
            serializedNode.children.forEach((child) =>
                node.append(this._unserializeNode(child, _map)[0])
            );
        } else {
            console.warn("unknown node type");
        }
        _map.set(node, serializedNode.nodeId);
        return [node, _map];
    }
}
