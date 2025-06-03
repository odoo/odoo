import { _t } from "@web/core/l10n/translation";
import { Plugin } from "../plugin";
import { childNodes, descendants, getCommonAncestor } from "../utils/dom_traversal";
import { hasTouch } from "@web/core/browser/feature_detection";
import { withSequence } from "@html_editor/utils/resource";
import { Deferred } from "@web/core/utils/concurrency";
import { toggleClass } from "@html_editor/utils/dom";
import { omit, pick } from "@web/core/utils/objects";

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
 * @property { string } value
 * @property { string } oldValue
 *
 * @typedef { Object } HistoryMutationAttributes
 * @property { "attributes" } type
 * // todo change id to nodeId
 * @property { string } id
 * @property { string } attributeName
 * @property { string } value
 * @property { string } oldValue
 *
 * @typedef { Object } HistoryMutationClassList
 * @property { "classList" } type
 * @property { string } id
 * @property { string } className
 * @property { boolean } value
 * @property { boolean } oldValue
 *
 * @typedef { Object } HistoryMutationAdd
 * @property { "add" } type
 * // todo change id to nodeId
 * @property { string } id
 * @property { string } parentId
 * @property { string } node
 * @property { string } nextId
 * @property { string } previousId
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
 * @typedef { HistoryMutationCharacterData | HistoryMutationAttributes | HistoryMutationClassList | HistoryMutationAdd | HistoryMutationRemove } HistoryMutation
 *
 * @typedef {Object} MutationRecordClassList
 * @property { "classList" } type
 * @property { Node } target
 * @property { string } className
 * @property { boolean } oldValue
 * @property { boolean } value
 *
 * @typedef {Object} MutationRecordAttributes
 * @property { "attributes" } type
 * @property { Node } target
 * @property { string } attributeName
 * @property { string } oldValue
 * @property { string } value
 *
 * @typedef {Object} MutationRecordCharacterData
 * @property { "characterData" } type
 * @property { Node } target
 * @property { string } oldValue
 * @property { string } value
 *
 * @typedef { MutationRecord | MutationRecordClassList | MutationRecordAttributes | MutationRecordCharacterData } HistoryMutationRecord
 *
 * @typedef { Object } PreviewableOperation
 * @property { Function } commit
 * @property { Function } preview
 * @property { Function } revert
 */

/**
 * @typedef { Object } HistoryShared
 * @property { HistoryPlugin['addCustomMutation'] } addCustomMutation
 * @property { HistoryPlugin['applyCustomMutation'] } applyCustomMutation
 * @property { HistoryPlugin['addExternalStep'] } addExternalStep
 * @property { HistoryPlugin['addStep'] } addStep
 * @property { HistoryPlugin['canRedo'] } canRedo
 * @property { HistoryPlugin['canUndo'] } canUndo
 * @property { HistoryPlugin['ignoreDOMMutations'] } ignoreDOMMutations
 * @property { HistoryPlugin['getHistorySteps'] } getHistorySteps
 * @property { HistoryPlugin['getNodeById'] } getNodeById
 * @property { HistoryPlugin['makePreviewableOperation'] } makePreviewableOperation
 * @property { HistoryPlugin['makePreviewableAsyncOperation'] } makePreviewableAsyncOperation
 * @property { HistoryPlugin['makeSavePoint'] } makeSavePoint
 * @property { HistoryPlugin['makeSnapshotStep'] } makeSnapshotStep
 * @property { HistoryPlugin['redo'] } redo
 * @property { HistoryPlugin['reset'] } reset
 * @property { HistoryPlugin['resetFromSteps'] } resetFromSteps
 * @property { HistoryPlugin['serializeSelection'] } serializeSelection
 * @property { HistoryPlugin['stageSelection'] } stageSelection
 * @property { HistoryPlugin['undo'] } undo
 * @property { HistoryPlugin['getIsPreviewing'] } getIsPreviewing
 * @property { HistoryPlugin['setStepExtra'] } setStepExtra
 * @property { HistoryPlugin['getIsCurrentStepModified'] } getIsCurrentStepModified
 */

export class HistoryPlugin extends Plugin {
    static id = "history";
    static dependencies = ["selection", "sanitize"];
    static shared = [
        "addCustomMutation",
        "applyCustomMutation",
        "addExternalStep",
        "addStep",
        "canRedo",
        "canUndo",
        "ignoreDOMMutations",
        "getHistorySteps",
        "getNodeById",
        "makePreviewableOperation",
        "makePreviewableAsyncOperation",
        "makeSavePoint",
        "makeSnapshotStep",
        "redo",
        "reset",
        "resetFromSteps",
        "serializeSelection",
        "stageSelection",
        "undo",
        "getIsPreviewing",
        "setStepExtra",
        "getIsCurrentStepModified",
    ];
    resources = {
        user_commands: [
            {
                id: "historyUndo",
                description: _t("Undo"),
                icon: "fa-undo",
                run: this.undo.bind(this),
            },
            {
                id: "historyRedo",
                description: _t("Redo"),
                icon: "fa-repeat",
                run: this.redo.bind(this),
            },
        ],
        ...(hasTouch() && {
            toolbar_groups: withSequence(5, { id: "historyMobile" }),
            toolbar_items: [
                {
                    id: "undo",
                    groupId: "historyMobile",
                    commandId: "historyUndo",
                    isDisabled: () => !this.canUndo(),
                    namespaces: ["compact", "expanded"],
                },
                {
                    id: "redo",
                    groupId: "historyMobile",
                    commandId: "historyRedo",
                    isDisabled: () => !this.canRedo(),
                    namespaces: ["compact", "expanded"],
                },
            ],
        }),
        shortcuts: [
            { hotkey: "control+z", commandId: "historyUndo" },
            { hotkey: "control+y", commandId: "historyRedo" },
            { hotkey: "control+shift+z", commandId: "historyRedo" },
        ],
        start_edition_handlers: () => {
            this.enableObserver();
            this.reset(this.config.content);
        },
        on_prepare_drag_handlers: this.disableIsCurrentStepModifiedWarning.bind(this),
        // Resource definitions:
        normalize_handlers: [
            // (commonRootOfModifiedEl or editableEl) => {
            //    clean up DOM before taking into account for next history step
            //    remaining in edit mode
            // }
        ],
    };

    setup() {
        this.mutationFilteredClasses = new Set(this.getResource("system_classes"));
        this.mutationFilteredAttributes = new Set(this.getResource("system_attributes"));
        this._onKeyupResetContenteditableNodes = [];
        this.addDomListener(this.document, "beforeinput", this._onDocumentBeforeInput.bind(this));
        this.addDomListener(this.document, "input", this._onDocumentInput.bind(this));
        this.addDomListener(this.editable, "pointerup", () => {
            this.stageSelection();
        });
        this.observer = new MutationObserver(this.handleNewRecords.bind(this));
        this.enableObserverCallbacks = new Set();
        this._cleanups.push(() => this.observer.disconnect());
        this.clean();
    }

    getIsPreviewing() {
        return this.isPreviewing;
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
            extraStepInfos: {},
        });
        /** @type { Map<string, "consumed"|"undo"|"redo"> } */
        this.stepsStates = new Map();
        this.nodeToIdMap = new WeakMap();
        this.idToNodeMap = new Map();
        /** @type { WeakMap<Node, { attributes: Map<string, string>, classList: Map<string, boolean>, characterData: Map<string, string> }> } */
        this.lastObservedState = new WeakMap();
        this.setNodeId(this.editable);
        this.dispatchTo("history_cleaned_handlers");
    }
    /**
     * @param {string} id
     * @returns {Node}
     */
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
        this.dispatchTo("history_reset_handlers", content);
    }
    /**
     * @param { HistoryStep[] } steps
     */
    resetFromSteps(steps) {
        this.withObserverOff(() => {
            this.editable.replaceChildren();
            this.clean();
            this.stageSelection();
            for (const step of steps) {
                this.applyMutations(step.mutations);
            }
            this.steps = steps;
            // todo: to test
            this.dispatchTo("history_reset_from_steps_handlers");
        });
        this.dispatchTo("history_reset_from_steps_handlers");
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
                parentId: "root",
                id: this.nodeToIdMap.get(node),
                node: this.serializeNode(node),
                nextId: null,
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
        for (const fn of this.getResource("history_step_processors")) {
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
     * Execute {@link callback} while the MutationObserver is disabled.
     *
     * /!\ This method should be used with extreme caution. Not observing some
     * mutations could lead to mutations that are impossible to undo/redo.
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
     * This is not shared as it is only used internally by the history plugin.
     * Other plugins should use {@link ignoreDOMMutations} instead.
     */
    withObserverOff(callback) {
        this.handleObserverRecords();
        this.observer.disconnect();
        callback();
        this.enableObserver();
    }

    handleObserverRecords() {
        this.handleNewRecords(this.observer.takeRecords());
    }

    /**
     * @param { MutationRecord[] } mutationRecords
     * @returns { HistoryMutationRecord[] }
     */
    processNewRecords(mutationRecords) {
        if (this.observer.takeRecords().length) {
            throw new Error("MutationObserver has pending records");
        }
        mutationRecords = this.filterMutationRecords(mutationRecords);
        /** @type {HistoryMutationRecord[]} */
        let records = mutationRecords
            .flatMap((record) => this.transformRecord(record))
            .filter((record) => !this.isSystemMutationRecord(record));

        records = this.handleUnobservedMutations(records);
        records = records.filter((record) => !this.isNoOpRecord(record));
        this.stageRecords(records);
        records
            .filter(({ type }) => type === "attributes")
            .forEach((record) => this.dispatchTo("attribute_change_handlers", record));
        return records;
    }

    /**
     * @param {HistoryMutationRecord} record
     */
    isNoOpRecord(record) {
        if (["attributes", "classList", "characterData"].includes(record.type)) {
            return record.value === record.oldValue;
        }
        return false;
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
        this.dispatchTo("content_updated_handlers", root);
    }

    /**
     * @param { MutationRecord[] } records
     */
    handleNewRecords(records) {
        const processedRecords = this.processNewRecords(records);
        if (processedRecords.length) {
            // TODO modify `handleMutations` of web_studio to handle
            // `undoOperation`
            const stepState = this.stepsStates.get(this.currentStep.id);
            this.getResource("handleNewRecords").forEach((cb) => cb(processedRecords, stepState));
            // Process potential new records adds by handleNewRecords.
            this.processNewRecords(this.observer.takeRecords());
            this.dispatchContentUpdated();
        }
    }

    /**
     * @param { MutationRecord[] } records
     */
    setIdOnRecords(records) {
        for (const record of records) {
            if (record.type === "childList") {
                for (const node of record.addedNodes) {
                    this.setNodeId(node);
                }
            }
        }
    }
    /**
     * @param { MutationRecord[] } records
     * @returns { MutationRecord[] }
     */
    filterMutationRecords(records) {
        this.dispatchTo("before_filter_mutation_record_handlers", records);
        for (const callback of this.getResource("savable_mutation_record_predicates")) {
            records = records.filter(callback);
        }
        records = this.filterAttributeMutationRecords(records);
        records = this.filterSameTextContentMutationRecords(records);
        records = this.filterOutIntermediateStateMutationRecords(records);
        return records;
    }

    /**
     * @param { MutationRecord[] } records
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
     * @param { MutationRecord[] } records
     * @returns { MutationRecord[] }
     */
    filterSameTextContentMutationRecords(records) {
        const filteredRecords = [];
        for (const record of records) {
            if (record.type === "childList" && this.isSameTextContentMutation(record)) {
                const { addedNodes, removedNodes } = record;
                const oldId = this.nodeToIdMap.get(removedNodes[0]);
                if (oldId) {
                    this.nodeToIdMap.delete(removedNodes[0]);
                    this.idToNodeMap.delete(oldId);
                    this.nodeToIdMap.set(addedNodes[0], oldId);
                    this.idToNodeMap.set(oldId, addedNodes[0]);
                }
                continue;
            }
            filteredRecords.push(record);
        }
        return filteredRecords;
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
     * @param { MutationRecord[] } records
     */
    filterOutIntermediateStateMutationRecords(records) {
        // Keep track of visited attributes of each node
        /** @type {Map<Node, Set<string>>} */
        const nodeToAttributes = new Map();
        // Keep track of visited nodes for characterData mutations
        /** @type {Set<Node>} */
        const visitedNodesCharData = new Set();
        const filteredRecords = [];
        for (const record of records) {
            if (record.type === "attributes") {
                // Add entry for current target if not already present.
                if (!nodeToAttributes.has(record.target)) {
                    nodeToAttributes.set(record.target, new Set());
                }
                const visitedAttributes = nodeToAttributes.get(record.target);
                // Keep only the first mutation record for each attribute.
                if (!visitedAttributes.has(record.attributeName)) {
                    filteredRecords.push(record);
                    visitedAttributes.add(record.attributeName);
                }
            } else if (record.type === "characterData") {
                // Keep only the first charData mutation record for each node.
                if (!visitedNodesCharData.has(record.target)) {
                    filteredRecords.push(record);
                    visitedNodesCharData.add(record.target);
                }
            } else {
                filteredRecords.push(record);
            }
        }
        return filteredRecords;
    }

    /**
     * Class attribute records are expanded into multiple classList records.
     * Attribute records have their oldValue normalized and new value added to it.
     * CharacterData records have new value added to it.
     *
     * @param { MutationRecord } record
     * @returns { HistoryMutationRecord | HistoryMutationRecord[] }
     */
    transformRecord(record) {
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
    }

    /**
     * Breaks down a class attribute mutation into individual class
     * addition/removal records for more precise history tracking.
     *
     * @param { MutationRecord } record of type "attributes" with attributeName === "class"
     * @returns { MutationRecordClassList[]}
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

        /** @type {(className: string, isAdded: boolean) => MutationRecordClassList } */
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

    /**
     * @param { HistoryMutationRecord } record
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
     * If the observer is disabled, store the last observed state of the
     * target's affected property (attribute/class/textContent) and drop the
     * record.
     *
     * Otherwise (observer enabled), update the record's `oldValue` with the
     * last observed state of that target's property.
     *
     * @param {HistoryMutationRecord[]} records
     * @returns {HistoryMutationRecord[]}
     */
    handleUnobservedMutations(records) {
        if (this.isObserverDisabled) {
            records.forEach((record) => this.storeOldValue(record));
            return [];
        }
        return records.map((record) => this.updateOldValue(record));
    }

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
     * @param {HistoryMutationRecord} record
     */
    storeOldValue(record) {
        if (record.type === "childList") {
            return;
        }
        const { stateMap, key } = this.getObservedStateStorage(record);
        // Only store it if not already stored.
        if (!stateMap.has(key)) {
            stateMap.set(key, record.oldValue);
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
     * @param {HistoryMutationRecord} record
     * @returns {HistoryMutationRecord}
     */
    updateOldValue(record) {
        if (record.type === "childList") {
            return record;
        }
        const { stateMap, key } = this.getObservedStateStorage(record);
        if (!stateMap.has(key)) {
            return record;
        }
        const lastObservedValue = stateMap.get(key);
        // Remove entry, so it won't be used again.
        stateMap.delete(key);
        return { ...record, oldValue: lastObservedValue };
    }

    /**
     * @param {HistoryMutationRecord} record
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
     * Check if a mutation consists of removing and adding a single text node
     * with the same text content, which occurs in Firefox but is optimized
     * away in Chrome.
     *
     * @param { MutationRecord } record
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
        const selection = this.dependencies.selection.getEditableSelection();
        if (this.getIsCurrentStepModified()) {
            console.warn(
                `should not have any "characterData", "remove" or "add" mutations in current step when you update the selection`
            );
            return;
        }
        this.currentStep.selection = this.serializeSelection(selection);
    }
    /**
     * @param { HistoryMutationRecord[] } records
     */
    stageRecords(records) {
        this.setIdOnRecords(records);
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
                case "characterData":
                case "classList":
                case "attributes": {
                    const id = this.nodeToIdMap.get(record.target);
                    this.currentStep.mutations.push({ ...omit(record, "target"), id });
                    break;
                }
                case "childList": {
                    this.currentStep.mutations.push(
                        ...this.splitChildListRecord(record, mutatedNodes)
                    );
                    break;
                }
            }
        }
    }

    /**
     * @param {MutationRecord} record of type "childList"
     * @param {Set<string>} mutatedNodes
     * @returns { (HistoryMutationRemove|HistoryMutationAdd)[] }
     */
    splitChildListRecord(record, mutatedNodes) {
        const parentId = this.nodeToIdMap.get(record.target);
        if (!parentId) {
            throw new Error("Unknown parent node");
        }

        const makeSingleNodeRecords = (nodes, type) =>
            nodes.map((node, index, nodeList) => {
                const [previousSibling, nextSibling] =
                    type === "add"
                        ? [nodeList[index - 1] || record.previousSibling, record.nextSibling]
                        : [record.previousSibling, nodeList[index + 1] || record.nextSibling];
                const [nextId, previousId] = [nextSibling, previousSibling].map((sibling) =>
                    // Preserve undefined and null values
                    sibling ? this.nodeToIdMap.get(sibling) : sibling
                );
                const id = this.nodeToIdMap.get(node);
                const serializedNode = this.serializeNode(
                    node,
                    type === "add" ? mutatedNodes : undefined
                );
                return { type, id, parentId, node: serializedNode, nextId, previousId };
            });

        // When nodes are expected to not be observed by the history, e.g.
        // because they belong to a distinct lifecycle such as interactions,
        // some operations such as replaceChildren might impact such a node
        // together with observed ones. Marking the node with skipHistoryHack
        // makes sure that it does not accidentally get observed during those
        // operations.
        // TODO Find a better solution.
        const skipHistoryHackFilter = (node) => !node.dataset?.skipHistoryHack;
        const removedNodes = [...record.removedNodes].filter(skipHistoryHackFilter);
        const addedNodes = [...record.addedNodes].filter(skipHistoryHackFilter);
        return [
            ...makeSingleNodeRecords(removedNodes, "remove"),
            ...makeSingleNodeRecords(addedNodes, "add"),
        ];
    }

    applyCustomMutation({ apply, revert }) {
        apply();
        this.addCustomMutation({ apply, revert });
    }

    addCustomMutation({ apply, revert }) {
        const customMutation = {
            type: "custom",
            apply: () => {
                apply();
                this.addCustomMutation({ apply, revert });
            },
            revert: () => {
                revert();
                this.addCustomMutation({ apply: revert, revert: apply });
            },
        };
        this.currentStep.mutations.push(customMutation);
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
     * @param {Object} [params.extraStepInfos]
     */
    addStep({ stepState, extraStepInfos } = {}) {
        // @todo @phoenix should we allow to pause the making of a step?
        // if (!this.stepsActive) {
        //     return;
        // }
        // @todo @phoenix link zws plugin
        // this._resetLinkZws();
        // @todo @phoenix sanitize plugin
        // this.sanitize();

        // Set the state of the step here.
        // That way, the state of undo and redo is truly accessible when
        // executing the onChange callback.
        // It is useful for external components if they execute shared.can[Undo|Redo]
        const currentStep = this.currentStep;
        if (stepState) {
            this.stepsStates.set(currentStep.id, stepState);
        }
        this.handleObserverRecords();
        const currentMutationsCount = currentStep.mutations.length;
        if (currentMutationsCount === 0) {
            return false;
        }
        const stepCommonAncestor = this.getMutationsRoot(currentStep.mutations) || this.editable;
        this.dispatchTo("normalize_handlers", stepCommonAncestor, stepState);
        this.handleObserverRecords();
        if (currentMutationsCount === currentStep.mutations.length) {
            // If there was no registered mutation during the normalization step,
            // force the dispatch of a content_updated to allow i.e. the hint
            // plugin to react to non-observed changes (i.e. a div becoming
            // a baseContainer).
            this.dispatchContentUpdated();
        }

        currentStep.previousStepId = this.steps.at(-1)?.id;

        this.steps.push(currentStep);
        // @todo @phoenix add this in the linkzws plugin.
        // this._setLinkZws();
        this.dispatchTo("before_add_step_handlers");
        if (extraStepInfos) {
            currentStep.extraStepInfos = extraStepInfos;
        }
        this.currentStep = this.processHistoryStep({
            id: this.generateId(),
            selection: {},
            mutations: [],
            previousStepId: undefined,
            extraStepInfos: {},
        });
        this.stageSelection();
        this.dispatchTo("step_added_handlers", {
            step: currentStep,
            stepCommonAncestor,
            isPreviewing: this.isPreviewing,
        });
        this.config.onChange?.({ isPreviewing: this.isPreviewing });
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
        let revertedStep;
        if (pos > 0) {
            // Consider the position consumed.
            revertedStep = this.steps[pos];
            this.stepsStates.set(revertedStep.id, "consumed");
            this.revertMutations(revertedStep.mutations, { forNewStep: true });
            this.setSerializedSelection(revertedStep.selection);
            this.addStep({ stepState: "undo", extraStepInfos: revertedStep.extraStepInfos });
            // Consider the last position of the history as an undo.
        }
        this.dispatchTo("post_undo_handlers", revertedStep);
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
        let revertedStep;
        if (pos > 0) {
            revertedStep = this.steps[pos];
            this.stepsStates.set(revertedStep.id, "consumed");
            this.revertMutations(revertedStep.mutations, { forNewStep: true });
            this.setSerializedSelection(revertedStep.selection);
            this.addStep({ stepState: "redo", extraStepInfos: revertedStep.extraStepInfos });
        }
        this.dispatchTo("post_redo_handlers", revertedStep);
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
        this.dependencies.selection.setSelection(newSelection, { normalize: false });
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
        const step = this.steps[index];
        if (!step) {
            return false;
        }
        return !this.getResource("unreversible_step_predicates").some((predicate) =>
            predicate(step)
        );
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
        this.withObserverOff(() => {
            // The last step is an uncommited draft, revert it first
            this.revertMutations(this.currentStep.mutations);

            const stepsAfterNewStep = this.steps.slice(index);

            for (const stepToRevert of stepsAfterNewStep.slice().reverse()) {
                this.revertMutations(stepToRevert.mutations);
            }
            this.applyMutations(newStep.mutations);
            this.dispatchTo(
                "normalize_handlers",
                this.getMutationsRoot(newStep.mutations) || this.editable
            );
            this.steps.splice(index, 0, newStep);
            for (const stepToApply of stepsAfterNewStep) {
                this.applyMutations(stepToApply.mutations);
            }
            // Reapply the uncommited draft, since this is not an operation which should cancel it
            this.applyMutations(this.currentStep.mutations);
            this.dispatchTo("external_step_added_handlers");
        });
    }
    /**
     * @param { HistoryMutation[] } mutations
     * @param { Object } options
     * @param { boolean } options.forNewStep whether the mutations will be used
     *        to create a new step
     * @param { boolean } options.reverse whether the mutations are the reverse
     *        of other mutations
     */
    applyMutations(mutations, { forNewStep = false, reverse } = {}) {
        for (const mutation of mutations) {
            switch (mutation.type) {
                case "custom": {
                    mutation.apply();
                    break;
                }
                case "characterData": {
                    const node = this.idToNodeMap.get(mutation.id);
                    if (node) {
                        node.textContent = mutation.value;
                    }
                    break;
                }
                case "classList": {
                    const node = this.idToNodeMap.get(mutation.id);
                    if (node) {
                        toggleClass(node, mutation.className, mutation.value);
                    }
                    break;
                }
                case "attributes": {
                    const node = this.idToNodeMap.get(mutation.id);
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
                                { forNewStep }
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
     * @param {HistoryMutationRemove} mutation
     */
    applyRemoveMutation(mutation) {
        const parent = this.idToNodeMap.get(mutation.parentId);
        const toRemove = this.idToNodeMap.get(mutation.id);
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
     * @param {HistoryMutationAdd} mutation
     */
    applyAddMutation(mutation) {
        const { id, node, parentId, nextId, previousId } = mutation;

        const toAdd = this.idToNodeMap.get(id) || this.unserializeNode(node);
        if (!toAdd) {
            return;
        }

        this.setNodeId(toAdd);

        const parent = this.idToNodeMap.get(parentId);
        if (!parent) {
            console.warn("Mutation could not be applied, parent node is missing.", mutation);
            return;
        }
        if (previousId === null) {
            parent.prepend(toAdd);
            return;
        }
        if (nextId === null) {
            parent.append(toAdd);
            return;
        }
        const isValid = (node) => node?.parentNode === parent;
        const [previousNode, nextNode] = [previousId, nextId].map((id) => this.idToNodeMap.get(id));
        if (isValid(previousNode)) {
            previousNode.after(toAdd);
            return;
        }
        if (isValid(nextNode)) {
            nextNode.before(toAdd);
            return;
        }
        console.warn("Mutation could not be applied, reference nodes are invalid.", mutation);
    }

    revertMutations(mutations, { forNewStep = false } = {}) {
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
        this.applyMutations(revertedMutations.toReversed(), { forNewStep, reverse: true });
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
        const selectionToRestore = this.dependencies.selection.preserveSelection();
        const extraToRestore = { ...this.currentStep.extraStepInfos };
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
            this.currentStep.extraStepInfos = extraToRestore;
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
                operation(...args);
                // todo: We should not add a step on preview as it would send
                // unnecessary steps in collaboration and let the other peer see
                // what we preview.
                //
                // The operation should be similar than in the 'commit'
                // (normalize etc...) hence the 'addStep' (but we need to remove
                // it for the collaboration).
                this.addStep();
            },
            commit: (...args) => {
                revertOperation();
                this.isPreviewing = false;
                operation(...args);
                this.addStep();
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
        let revertOperation = () => {};

        return {
            preview: async (...args) => {
                revertOperation();
                const def = new Deferred();
                const revertSavePoint = this.makeSavePoint();
                revertOperation = async () => {
                    await def;
                    revertSavePoint();
                };
                this.isPreviewing = true;
                await operation(...args);
                def.resolve();
                // todo: We should not add a step on preview as it would send
                // unnecessary steps in collaboration and let the other peer see
                // what we preview.
                //
                // The operation should be similar than in the 'commit'
                // (normalize etc...) hence the 'addStep' (but we need to remove
                // it for the collaboration).
                this.addStep();
            },
            commit: async (...args) => {
                revertOperation();
                this.isPreviewing = false;
                await operation(...args);
                this.addStep();
            },
            revert: async () => {
                await revertOperation();
                revertOperation = () => {};
                this.isPreviewing = false;
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

    setStepExtra(key, value) {
        this.currentStep.extraStepInfos[key] = value;
    }

    disableIsCurrentStepModifiedWarning() {
        this.ignoreIsCurrentStepModified = true;
        return () => {
            this.ignoreIsCurrentStepModified = false;
        };
    }

    getIsCurrentStepModified() {
        if (this.ignoreIsCurrentStepModified) {
            return false;
        }
        return this.currentStep.mutations.find((m) =>
            ["characterData", "remove", "add"].includes(m.type)
        );
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
     * Serialize a node and its children if the collaboration is true.
     * @param { Node } node
     * @param { Set<Node> } nodesToStripFromChildren
     */
    serializeNode(node, mutatedNodes) {
        return this._serializeNode(node, mutatedNodes, this.nodeToIdMap);
    }
    /**
     * Unserialize a node and its children if the collaboration is true.
     *
     * TODO: find a solution so that the following issue can never happen:
     *   If there is already another node in `nodeToIdMap` pointing to the
     *   current id before executing `this.nodeToIdMap.set(node, id)` in this
     *   function, there will be 2 different nodes pointing to the same id.
     *
     *   2 different nodes for the same id is pretty common:
     *     Unserializing a text node in `_unserializeNode` always creates
     *     another (new) node.
     *
     *   If mutations concerning both nodes are bundled in the same step, they
     *   will all be erroneously serialized as if they concern the node which
     *   had its id set the latest, which is likely to cause issues when
     *   applying these mutations (undo/redo, collaboration).
     *
     * @param { SerializedNode } node
     * @returns { Node }
     */
    unserializeNode(node) {
        let [unserializedNode, nodeMap] = this._unserializeNode(node, this.idToNodeMap);
        const fakeNode = this.document.createElement("fake-el");
        fakeNode.appendChild(unserializedNode);
        this.dependencies.sanitize.sanitize(fakeNode, { IN_PLACE: true });
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
            let childrenToSerialize = childNodes(node);
            for (const cb of this.getResource("serializable_descendants_processors")) {
                childrenToSerialize = cb(node, childrenToSerialize);
            }
            result.tagName = node.tagName;
            result.children = [];
            result.attributes = {};
            for (let i = 0; i < node.attributes.length; i++) {
                result.attributes[node.attributes[i].name] = node.attributes[i].value;
            }
            for (const child of childrenToSerialize) {
                if (!nodesToStripFromChildren.has(this.nodeToIdMap.get(child))) {
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
        if (this.editable.contains(ev.target)) {
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
