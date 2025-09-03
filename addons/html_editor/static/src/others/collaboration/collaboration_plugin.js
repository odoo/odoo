import { Plugin } from "@html_editor/plugin";

// 60 seconds
export const HISTORY_SNAPSHOT_INTERVAL = 1000 * 60;
// 10 seconds
const HISTORY_SNAPSHOT_BUFFER_TIME = 1000 * 10;

/**
 * @typedef { Object } CollaborationPluginConfig
 * @property { string } peerId
 *
 * @typedef { import("../../core/history_plugin").HistoryStep } HistoryStep
 */

/**
 * @typedef { Object } CollaborationShared
 * @property { CollaborationPlugin['getBranchIds'] } getBranchIds
 * @property { CollaborationPlugin['getSnapshotSteps'] } getSnapshotSteps
 * @property { CollaborationPlugin['historyGetMissingSteps'] } historyGetMissingSteps
 * @property { CollaborationPlugin['onExternalHistorySteps'] } onExternalHistorySteps
 * @property { CollaborationPlugin['resetFromSteps'] } resetFromSteps
 * @property { CollaborationPlugin['setInitialBranchStepId'] } setInitialBranchStepId
 */

export class CollaborationPlugin extends Plugin {
    static id = "collaboration";
    static dependencies = ["history", "selection", "sanitize"];
    resources = {
        /** Handlers */
        history_cleaned_handlers: this.onHistoryClean.bind(this),
        history_reset_handlers: this.onHistoryReset.bind(this),
        step_added_handlers: ({ step }) => this.onStepAdded(step),

        /** Overrides */
        set_attribute_overrides: this.setAttribute.bind(this),

        history_step_processors: this.processHistoryStep.bind(this),
        unreversible_step_predicates: this.isUnreversibleStep.bind(this),
    };
    static shared = [
        "getBranchIds",
        "getSnapshotSteps",
        "historyGetMissingSteps",
        "onExternalHistorySteps",
        "resetFromSteps",
        "setInitialBranchStepId",
    ];

    /** @type { CollaborationPluginConfig['peerId'] } */
    peerId = null;

    setup() {
        this.peerId = this.config.collaboration.peerId;
        if (!this.peerId) {
            throw new Error("The collaboration plugin requires a peerId");
        }
        this._snapshotInterval = setInterval(() => {
            this.makeSnapshot();
        }, HISTORY_SNAPSHOT_INTERVAL);
    }

    destroy() {
        super.destroy();
        clearInterval(this._snapshotInterval);
        this._snapshotInterval = false;
    }

    onHistoryClean() {
        this.branchStepIds = [];
    }
    onHistoryReset() {
        const firstStep = this.dependencies.history.getHistorySteps()[0];
        this.snapshots = [{ step: firstStep }];
    }
    /**
     * @param {HistoryStep} step
     */
    isUnreversibleStep(step) {
        return step.peerId !== this.peerId;
    }
    /**
     * @param {Node} node
     * @param {string} attributeName
     * @param {string} attributeValue
     */
    setAttribute(node, attributeName, attributeValue) {
        if (attributeValue) {
            this.safeSetAttribute(node, attributeName, attributeValue);
            return true;
        }
    }

    /**
     * Get all the history ids for the current history branch.
     */
    getBranchIds() {
        const steps = this.dependencies.history.getHistorySteps();
        return (this.initialBranchStepId || "")
            .split(",")
            .concat(this.branchStepIds)
            .concat(steps.map((s) => s.id));
    }
    /**
     * Safely set an attribute on a node.
     * @param {HTMLElement} node
     * @param {string} attributeName
     * @param {string} attributeValue
     */
    safeSetAttribute(node, attributeName, attributeValue) {
        const clone = this.document.createElement(node.tagName);
        clone.setAttribute(attributeName, attributeValue);
        this.dependencies.sanitize.sanitize(clone);
        if (clone.hasAttribute(attributeName)) {
            node.setAttribute(attributeName, clone.getAttribute(attributeName));
        } else {
            node.removeAttribute(attributeName);
        }
    }

    /**
     * Apply external steps coming from the collaboration.
     *
     * @param {Object} newSteps External steps to be applied
     */
    onExternalHistorySteps(newSteps) {
        let stepIndex = 0;
        const selectionData = this.dependencies.selection.getSelectionData();

        const steps = this.dependencies.history.getHistorySteps();
        for (const newStep of newSteps) {
            // todo: add a test that no 2 history_missing_parent_step_handlers
            // are called in same stack.
            const insertIndex = this.getInsertStepIndex(steps, newStep);
            if (typeof insertIndex === "undefined") {
                continue;
            }
            this.dependencies.history.addExternalStep(newStep, insertIndex);
            stepIndex++;
        }
        if (selectionData.documentSelectionIsInEditable) {
            this.dependencies.selection.rectifySelection(selectionData.editableSelection);
        }

        this.dispatchTo("external_history_step_handlers");

        // todo: ensure that if the selection was not in the editable before the
        // reset, it remains where it was after applying the snapshot.

        if (stepIndex) {
            this.config.onChange?.();
        }
    }

    /**
     * @param {HistoryStep[]} steps
     * @param {HistoryStep} newStep
     */
    getInsertStepIndex(steps, newStep) {
        let index = steps.length - 1;
        while (index >= 0 && steps[index].id !== newStep.previousStepId) {
            // Skip steps that are already in the list.
            if (steps[index].id === newStep.id) {
                return;
            }
            index--;
        }

        // When the previousStepId is not present in the steps it
        // could be either:
        // - the previousStepId is before a snapshot of the same history
        // - the previousStepId has not been received because peers were
        //   disconnected at that time
        // - the previousStepId is in another history (in case two totally
        //   differents `steps` (but it should not arise)).
        if (index < 0) {
            const historySteps = steps;
            let index = historySteps.length - 1;
            // Get the last known step that we are sure the missing step
            // peer has. It could either be a step that has the same
            // peerId or the first step.
            while (index !== 0) {
                if (historySteps[index].peerId === newStep.peerId) {
                    break;
                }
                index--;
            }
            const fromStepId = historySteps[index].id;
            this.dispatchTo("history_missing_parent_step_handlers", {
                step: newStep,
                fromStepId: fromStepId,
            });
            return;
        }

        let concurentSteps = [];
        index++;
        while (index < steps.length) {
            if (steps[index].previousStepId === newStep.previousStepId) {
                if (steps[index].id.localeCompare(newStep.id) === 1) {
                    break;
                } else {
                    concurentSteps = [steps[index].id];
                }
            } else {
                if (concurentSteps.includes(steps[index].previousStepId)) {
                    concurentSteps.push(steps[index].id);
                } else {
                    break;
                }
            }
            index++;
        }

        return index;
    }

    /**
     * @param {Object} params
     * @param {string} params.fromStepId
     * @param {string} [params.toStepId]
     */
    historyGetMissingSteps({ fromStepId, toStepId }) {
        const steps = this.dependencies.history.getHistorySteps();
        const fromIndex = steps.findIndex((x) => x.id === fromStepId);
        const toIndex = toStepId ? steps.findIndex((x) => x.id === toStepId) : steps.length;
        if (fromIndex === -1 || toIndex === -1) {
            return -1;
        }
        return steps.slice(fromIndex + 1, toIndex);
    }

    getSnapshotSteps() {
        const historySteps = this.dependencies.history.getHistorySteps();
        // If the current snapshot has no time, it means that there is the no
        // other snapshot that have been made (either it is the one created upon
        // initialization or reseted by history's resetFromSteps).
        if (!this.snapshots[0].time) {
            return { steps: historySteps, historyIds: this.getBranchIds() };
        }
        const snapshotSteps = [];
        let snapshot;
        if (this.snapshots[0].time + HISTORY_SNAPSHOT_BUFFER_TIME < Date.now()) {
            snapshot = this.snapshots[0];
        } else {
            // this.snapshots[1] has being created at least 1 minute ago
            // (HISTORY_SNAPSHOT_INTERVAL) or it is the first step.
            snapshot = this.snapshots[1];
        }
        let index = historySteps.length - 1;
        while (historySteps[index].id !== snapshot.step.id) {
            snapshotSteps.push(historySteps[index]);
            index--;
        }
        snapshotSteps.push(snapshot.step);
        snapshotSteps.reverse();

        return { steps: snapshotSteps, historyIds: this.getBranchIds() };
    }
    setInitialBranchStepId(stepId) {
        this.initialBranchStepId = stepId;
    }
    resetFromSteps(steps, branchStepIds) {
        this.dependencies.selection.resetSelection();
        this.dependencies.history.resetFromSteps(steps);
        this.snapshots = [{ step: steps[0] }];
        this.branchStepIds = branchStepIds;

        // @todo @phoenix: test that the hint are proprely handeled
        // this._handleCommandHint();
        // @todo @phoenix: make the multiselection
        // this.multiselectionRefresh();
        // @todo @phoenix: check it is still relevant
        // this.dispatchEvent(new Event("resetFromSteps"));
    }

    makeSnapshot() {
        const historyLength = this.dependencies.history.getHistorySteps().length;
        if (!this.lastSnapshotLength || this.lastSnapshotLength < historyLength) {
            this.lastSnapshotLength = historyLength;
            const step = this.dependencies.history.makeSnapshotStep();
            const snapshot = {
                time: Date.now(),
                step: step,
            };
            this.snapshots = [snapshot, this.snapshots[0]];
        }
    }

    /**
     * @param {HistoryStep} step
     */
    onStepAdded(step) {
        step.peerId = this.peerId;
        this.dispatchTo("collaboration_step_added_handlers", step);
    }
    /**
     * @param {HistoryStep} step
     */
    processHistoryStep(step) {
        step.peerId = this.peerId;
        return step;
    }
}
