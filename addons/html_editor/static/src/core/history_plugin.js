import { Plugin } from "../plugin";
import { hasTouch } from "@web/core/browser/feature_detection";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef { import("./selection_plugin").EditorSelection } EditorSelection
 * @typedef { import("../utils/dom_map").SerializedNode } SerializedNode
 * @typedef { import("../utils/dom_map").SerializedSelection } SerializedSelection
 * @typedef { import("../utils/dom_map").NodeId } NodeId
 *
 * @typedef { string } HistoryStepId
 * @typedef { "original"|"undo"|"redo"|"restore"|"reset" } HistoryStepType
 *
 * @typedef { Object } HistoryStep
 * @property { HistoryStepId } id
 * @property { HistoryStepType } type
 * @property { EditorCommit } commit
 * @property { HistoryStepId } previousStepId
 *
 * @typedef { import("./dom_mutation_plugin").EditorMutation } EditorMutation
 * @typedef { import("./dom_mutation_plugin").EditorMutationRecord } EditorMutationRecord
 * @typedef { import("./dom_mutation_plugin").EditorCommit } EditorCommit
 */
/**
 * @typedef { Object } HistoryShared
 * @property { HistoryPlugin['write'] } write
 * @property { HistoryPlugin['undo'] } undo
 * @property { HistoryPlugin['redo'] } redo
 * @property { HistoryPlugin['addExternalStep'] } addExternalStep
 * @property { HistoryPlugin['canRedo'] } canRedo
 * @property { HistoryPlugin['canUndo'] } canUndo
 * @property { HistoryPlugin['getHistorySteps'] } getHistorySteps
 * @property { HistoryPlugin['reset'] } reset
 * @property { HistoryPlugin['resetFromSteps'] } resetFromSteps
 * @property { HistoryPlugin['getCommitsUntil'] } getCommitsUntil
 */
/**
 * @typedef {((record: EditorMutationRecord) => void)[]} attribute_change_handlers
 * @typedef {((records: EditorMutationRecord[]) => void)[]} before_filter_mutation_record_handlers
 * @typedef {(() => void)[]} external_step_added_handlers
 * @typedef {(() => void)[]} history_cleaned_handlers
 * @typedef {(() => void)[]} history_reset_handlers
 * @typedef {(() => void)[]} history_reset_from_steps_handlers
 * @typedef {((revertedStep: HistoryStep) => void)[]} post_redo_handlers
 * @typedef {((revertedStep: HistoryStep) => void)[]} post_undo_handlers
 * @typedef {((step: HistoryStep) => void)[]} step_added_handlers
 *
 * @typedef {((record: EditorMutationRecord) => boolean)[]} savable_mutation_record_predicates
 * @typedef {((step: HistoryStep) => boolean)[]} unreversible_step_predicates
 *
 * @typedef {((
 *    arg: {
 *      target: Node,
 *      attributeName: string,
 *      oldValue: string,
 *      value: string,
 *      reverse: boolean,
 *    },
 *    options: { ensureNewMutations: boolean }
 *  ) => void)[]} attribute_change_processors
 * @typedef {((step: HistoryStep) => HistoryStep)[]} history_step_processors
 * @typedef {((node: Node, attributeName: string, attributeValue: string) => boolean)[]} set_attribute_overrides
 */

export const STEP_DEBOUNCE_DELAY = 250;

export class HistoryPlugin extends Plugin {
    static id = "history";
    static dependencies = ["selection"];
    static shared = [
        // Main
        "write",
        "undo",
        "redo",
        // From original
        "addExternalStep",
        "canRedo",
        "canUndo",
        "getHistorySteps",
        "reset",
        "resetFromSteps",
        // Had to add
        "getCommitsUntil",
        "createStep", // should it get processed or just raw?
    ];
    /** @type {import("plugins").EditorResources} */
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
            { hotkey: "control+z", commandId: "historyUndo", global: true },
            { hotkey: "control+y", commandId: "historyRedo", global: true },
            { hotkey: "control+shift+z", commandId: "historyRedo", global: true },
        ],
        start_edition_handlers: () => {
            this.reset(this.config.content);
        },
    };

    setup() {
        this._onKeyupResetContenteditableNodes = [];
        this.addDomListener(this.document, "beforeinput", this._onDocumentBeforeInput.bind(this));
        this.addDomListener(this.document, "input", this._onDocumentInput.bind(this));
        this.clean();
    }

    /**
     * @param { EditorCommit[] } commit
     * @param { HistoryStepType } [type = "original"]
     */
    write(commit, type = "original") {
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
        // It is useful for external components if they execute
        // shared.can(Undo|Redo)
        // TODO AGE: the comment above mentions a link between config.onChange
        // and can(Undo|Redo) -> should we call config.onChange here instead of
        // in domMutation?
        const currentStep = this.createStep(commit, type);

        this.steps.push(currentStep);
        // @todo @phoenix add this in the linkzws plugin.
        // this._setLinkZws();
        // TODO AGE: find a better way? This is just because before my changes
        // reset caused a step without calling addStep but by using steps.push
        // directly.
        if (type !== "reset") {
            this.dispatchTo("step_added_handlers", currentStep);
        }
        return currentStep;
    }

    undo() {
        if (this.steps.length === 1) {
            return;
        }
        this.dispatchTo("pre_undo_handlers");
        const pos = this.getNextUndoIndex();
        let revertedStep;
        if (pos > 0) {
            revertedStep = this.steps[pos];
            this.revertStep(revertedStep, { ensureNewMutations: true });
            this.revertedSteps.add(revertedStep.id);
        }
        this.dispatchTo("post_undo_handlers", revertedStep);
    }

    redo() {
        this.dispatchTo("pre_redo_handlers");
        const pos = this.getNextRedoIndex();
        let revertedStep;
        if (pos > 0) {
            revertedStep = this.steps[pos];
            this.revertStep(revertedStep, { ensureNewMutations: true });
            this.revertedSteps.add(revertedStep.id);
        }
        this.dispatchTo("post_redo_handlers", revertedStep);
    }

    // Private

    applyStep(step) {
        this.delegateTo("apply_commit_overrides", step.commit);
    }

    revertStep(step, { ensureNewMutations = false } = {}) {
        this.delegateTo("revert_commit_overrides", step.commit, { ensureNewMutations });
    }

    clean() {
        /** @type { HistoryStep[] } */
        this.steps = [];
        /** @type {Set<HistoryStepId>} Steps reverted by undo/redo operations */
        this.revertedSteps = new Set();
        /** @type {Set<HistoryStepId>} Steps reverted by restoring to a save point */
        this.discardedSteps = new Set();
        this.dispatchTo("history_cleaned_handlers");
    }

    /**
     * Reset the history.
     *
     * @param { string } content
     */
    reset(content) {
        this.clean();
        this.dispatchTo("history_reset_handlers", content);
    }

    // NEW: process commit

    /**
     * @param {EditorCommit} commit
     * @param { HistoryStepType } type
     * @returns { HistoryStep }
     */
    createStep(commit, type) {
        return this.processHistoryStep({
            id: commit.id,
            type,
            commit,
            previousStepId: this.steps.at(-1)?.id,
        });
    }

    // Steps

    /**
     * @param { HistoryStep } step
     * @returns { HistoryStep }
     */
    processHistoryStep(step) {
        for (const fn of this.getResource("history_step_processors")) {
            step = fn(step);
        }
        return step;
    }

    /**
     * Insert a step in the history.
     *
     * @param { HistoryStep } newStep
     * @param { number } index
     */
    addExternalStep(newStep, index) {
        this.dispatchTo("before_add_external_step_handlers");
        const stepsAfterNewStep = this.steps.slice(index);
        for (const stepToRevert of stepsAfterNewStep.slice().reverse()) {
            this.revertStep(stepToRevert);
        }
        this.applyStep(newStep);
        // TODO AGE: could we avoid this?
        let root;
        this.getResource("node_by_id_providers").find((p) => {
            root = p(newStep.commit.root);
            return root;
        });
        this.dispatchTo("normalize_handlers", root);
        this.steps.splice(index, 0, newStep);
        for (const stepToApply of stepsAfterNewStep) {
            this.applyStep(stepToApply);
        }
        this.dispatchTo("external_step_added_handlers");
    }

    getHistorySteps() {
        return this.steps;
    }

    // Before applying a step

    canUndo() {
        return this.getNextUndoIndex() > 0;
    }

    canRedo() {
        return this.getNextRedoIndex() > 0;
    }

    /**
     * Get the step index in the history to undo.
     * Return -1 if no undo index can be found.
     *
     * @param { number } fromIndex step index from which to search
     */
    getNextUndoIndex() {
        // Go back to first step that can be undone ("original", "reset" or "redo").
        for (let index = this.steps.length - 1; index >= 0; index--) {
            const step = this.steps[index];
            if (!this.isReversibleStep(step) || this.discardedSteps.has(step.id)) {
                continue;
            }
            if (
                ["original", "reset", "redo"].includes(step.type) &&
                !this.revertedSteps.has(step.id)
            ) {
                return index;
            }
        }
        // There is no steps left to be undone, return an index that does not
        // point to any step
        return -1;
    }
    /**
     * Get the step index in the history to redo.
     * Return -1 if no redo index can be found.
     *
     * @param { number } fromIndex step index from which to search
     */
    getNextRedoIndex(fromIndex = this.steps.length) {
        // Look for an "undo" step that has not yet been redone. Stop search if
        // a "original" step is found.
        for (let index = fromIndex - 1; index >= 0; index--) {
            const step = this.steps[index];
            if (!this.isReversibleStep(step) || this.discardedSteps.has(step.id)) {
                continue;
            }
            if (["original", "reset"].includes(step.type)) {
                return -1;
            }
            if (step.type === "undo" && !this.revertedSteps.has(step.id)) {
                return index;
            }
        }
        return -1;
    }

    // Applying a step

    /**
     * Get the commits saved in steps between the step of given id (not
     * included) and the most recent one. If no step id is given, return all
     * commits but the first.
     *
     * @param {HistoryStepId} [stepId]
     * @returns { { ...EditorCommit, discard: false | () => void }[] }
     */
    getCommitsUntil(stepId) {
        const stepIndex = this.steps.findLastIndex((step) => step?.id === stepId);
        return this.steps
            .slice(stepIndex === -1 ? 1 : stepIndex + 1)
            .map((step) => {
                if (step.commit && this.isReversibleStep(step)) {
                    step.commit.discard = () => {
                        this.discardedSteps.add(step.id);
                    };
                }
                return step.commit;
            })
            .filter(Boolean)
            .reverse();
    }

    /**
     * Meant to be overriden.
     *
     * @param { HistoryStep } step
     */
    isReversibleStep(step) {
        return !this.getResource("unreversible_step_predicates").some((predicate) =>
            predicate(step)
        );
    }

    /**
     * @param { HistoryStep[] } steps
     */
    resetFromSteps(steps) {
        this.dispatchTo("before_history_reset_from_steps_handlers");
        this.editable.replaceChildren();
        this.clean();
        steps.forEach(this.applyStep.bind(this));
        this.steps = steps;
        // todo: to test
        this.dispatchTo("history_reset_from_steps_handlers");
        // TODO AGE: all this was wrapped in a `domMutations.withObserverOff`,
        // and there was a dispatch to history_reset_from_steps_handlers at the
        // end of the callback _and_ after the call to `withObserverOff`. I
        // replaced the `withObserverOff` with disabling/enabling the observer
        // in the resources dispatched here. So I wasn't able to put this second
        // dispatch again. Why was it needed?
    }

    // Listeners to handle contenteditable stuff

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
