import { Plugin } from "@html_editor/plugin";

// 60 seconds
export const HISTORY_SNAPSHOT_INTERVAL = 1000 * 60;
// 10 seconds
const HISTORY_SNAPSHOT_BUFFER_TIME = 1000 * 10;

/**
 * @typedef { Object } CollaborationPluginConfig
 * @property { string } peerId
 */

export class CollaborationPlugin extends Plugin {
    static name = "collaboration";
    static dependencies = ["history", "selection", "sanitize"];
    /** @type { (p: CollaborationPlugin) => Record<string, any> } */
    static resources = (p) => ({
        set_attribute: p.setAttribute.bind(p),
        process_history_step: p.processHistoryStep.bind(p),
        is_reversible_step: p.isReversibleStep.bind(p),
    });
    static shared = [
        //
        "onExternalHistorySteps",
        "historyGetMissingSteps",
        "setInitialBranchStepId",
        "getBranchIds",
        "getSnapshotSteps",
        "resetFromSteps",
    ];
    handleCommand(commandName, payload) {
        switch (commandName) {
            case "STEP_ADDED": {
                this.onStepAdded(payload.step);
                break;
            }
            case "HISTORY_CLEAN": {
                this.onHistoryClean();
                break;
            }
            case "HISTORY_RESET": {
                this.resetSnapshots();
                break;
            }
        }
    }

    externalStepsBuffers = [];
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
    resetSnapshots() {
        const firstStep = this.shared.getHistorySteps()[0];
        this.snapshots = [{ step: firstStep }];
    }
    /**
     * @param {number} index
     */
    isReversibleStep(index) {
        const steps = this.shared.getHistorySteps();
        const step = steps[index];
        return step && step.peerId === this.peerId;
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
        const steps = this.shared.getHistorySteps();
        return [this.initialBranchStepId].concat(this.branchStepIds).concat(steps.map((s) => s.id));
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
        this.shared.sanitize(clone);
        if (clone.hasAttribute(attributeName)) {
            node.setAttribute(attributeName, clone.getAttribute(attributeName));
        } else {
            node.removeAttribute(attributeName);
        }
    }

    /**
     * Apply external steps coming from the collaboration. Buffer them if
     * postProcessExternalStepsPromise is not null until it is resolved (since
     * steps could potentially concern elements currently being rendered
     * asynchronously).
     *
     * @param {Object} newSteps External steps to be applied
     */
    onExternalHistorySteps(newSteps, originPeerId) {
        if (this.postProcessExternalStepsPromise) {
            this.externalStepsBuffers.push([newSteps, originPeerId]);
        }
        this.shared.disableObserver();
        const selection = this.shared.getEditableSelection();

        let stepIndex = 0;
        const steps = this.shared.getHistorySteps();
        for (const newStep of newSteps) {
            const insertIndex = this.getInsertStepIndex(steps, newStep);
            if (insertIndex === "missingSteps") {
                if (insertIndex === "missingSteps") {
                    this.requestMissingSteps(steps, newStep, originPeerId);
                    return;
                }
            }
            if (typeof insertIndex === "undefined") {
                continue;
            }
            this.shared.addExternalStep(newStep, insertIndex);
            stepIndex++;

            this.postProcessExternalSteps();
            if (this.postProcessExternalStepsPromise) {
                this.postProcessExternalStepsPromise = this.postProcessExternalStepsPromise.then(
                    () => {
                        this.postProcessExternalStepsPromise = undefined;
                        const buffers = this.externalStepsBuffers;
                        this.externalStepsBuffers = [];
                        for (const [steps, originId] of buffers) {
                            this.onExternalHistorySteps(steps, originId);
                        }
                    }
                );
                this.externalStepsBuffers.push([newSteps.slice(stepIndex), originPeerId]);
                break;
            }
        }

        this.shared.enableObserver();
        if (selection.inEditable) {
            this.shared.rectifySelection(selection);
        }

        this.resources.onExternalHistorySteps?.forEach((cb) => cb());
    }
    requestMissingSteps(steps, newStep, originPeerId) {
        const historySteps = steps;
        let index = historySteps.length - 1;
        // Get the last known step of the peer.
        while (index !== 0) {
            if (historySteps[index].peerId === originPeerId) {
                break;
            }
            index--;
        }
        const fromStepId = historySteps[index].id;
        for (const cb of this.resources.onExternalMissingParentStep || []) {
            cb({ step: newStep, fromStepId, originPeerId });
        }
    }

    /**
     * @param {import("../../core/history_plugin").HistoryStep[]} steps
     * @param {import("../../core/history_plugin").HistoryStep} newStep
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
            return "missingSteps";
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
        const steps = this.shared.getHistorySteps();
        const fromIndex = steps.findIndex((x) => x.id === fromStepId);
        const toIndex = toStepId ? steps.findIndex((x) => x.id === toStepId) : steps.length;
        if (fromIndex === -1 || toIndex === -1) {
            return -1;
        }
        return steps.slice(fromIndex + 1, toIndex);
    }

    getSnapshotSteps() {
        const historySteps = this.shared.getHistorySteps();
        // If the current snapshot has no time, it means that there is the no
        // other snapshot that have been made (either it is the one created upon
        // initialization or reseted by historyResetFromSteps).
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
        this.shared.resetSelection();
        this.shared.historyResetFromSteps(steps);
        this.branchStepIds = branchStepIds;
        this.postProcessExternalSteps();
        this.shared.enableObserver();

        // @todo @phoenix: test that the hint are proprely handeled
        // this._handleCommandHint();
        // @todo @phoenix: make the multiselection
        // this.multiselectionRefresh();
    }
    postProcessExternalSteps() {
        const postProcessExternalSteps = this.resources["post_process_external_steps"]
            ?.map((cb) => cb(this.editable))
            ?.filter(Boolean);
        if (postProcessExternalSteps?.length) {
            this.postProcessExternalStepsPromise = Promise.all(postProcessExternalSteps);
        }
    }

    makeSnapshot() {
        const historyLength = this.shared.getHistorySteps().length;
        if (!this.lastSnapshotLength || this.lastSnapshotLength < historyLength) {
            this.lastSnapshotLength = historyLength;
            const step = this.shared.makeSnapshotStep();
            const snapshot = {
                time: Date.now(),
                step: step,
            };
            this.snapshots = [snapshot, this.snapshots[0]];
        }
    }

    /**
     * @param {import("../../core/history_plugin").HistoryStep} step
     */
    onStepAdded(step) {
        step.peerId = this.peerId;
        this.dispatch("COLLABORATION_STEP_ADDED", step);
    }
    /**
     * @param {import("../../core/history_plugin").HistoryStep} step
     */
    processHistoryStep(step) {
        step.peerId = this.peerId;
        return step;
    }
}
