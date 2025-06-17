import { Plugin } from "@html_editor/plugin";

/**
 * @typedef {Class} BuilderAction
 * @property {string} id
 * @property {Function} apply
 * @property {Function} [isApplied]
 * @property {Function} [clean]
 * @property {() => Promise<any>} [load]
 */
export class BuilderActionsPlugin extends Plugin {
    static id = "builderActions";
    static shared = ["getAction", "applyAction", "callApplySpecs"];
    static dependencies = ["operation", "history"];
    setup() {
        this.actions = {};
        for (const actions of this.getResource("builder_actions")) {
            for (const [actionKey, Action] of Object.entries(actions)) {
                if (actionKey in this.actions) {
                    throw new Error(`Duplicate builder action id: ${actionKey}`);
                }
                if (Action.constructor.name === "Function") {
                    const deps = {};
                    for (const depName of Action.dependencies) {
                        deps[depName] = this.config.getShared()[depName];
                    }
                    this.actions[Action.id] = new Action(this, deps);
                } else {
                    this.actions[actionKey] = { id: actionKey, ...Action };
                }
            }
        }
        Object.freeze(this.actions);
    }

    /**
     * Get the action object for the given action ID.
     *
     * @param {string} actionId
     * @returns {Object}
     */
    getAction(actionId) {
        const action = this.actions[actionId];
        if (!action) {
            throw new Error(`Unknown builder action id: ${actionId}`);
        }
        return action;
    }

    /**
     * Apply action for the given action ID.
     *
     * @param {string} actionId
     * @param {Object} spec
     */
    applyAction(actionId, spec) {
        const action = this.getAction(actionId);
        this.dependencies.operation.next(
            async () => {
                await action.apply(spec);
                this.dependencies.history.addStep();
            },
            {
                ...action,
                load: async () => {
                    if (action.load) {
                        const loadResult = await action.load(spec);
                        spec.loadResult = loadResult;
                    }
                },
            }
        );
    }

    /**
     * TODO
     * @param applySpecs
     * @param isPreviewing
     * @param callback
     * @returns {Promise<Awaited<unknown>[]>}
     */
    async _forEachApplySpec(applySpecs, isPreviewing, callback) {
        const proms = [];
        for (const applySpec of applySpecs) {
            const result = callback(applySpec);
            proms.push(result);

            // If result is a promise, this means apply or clean is async. If we're previewing, this is bad practice.
            // We discourage this practice with a warning.
            const isPromise = typeof result?.then === "function";
            if (isPreviewing && isPromise) {
                const action = this.getAction(applySpec.actionId);
                if (!action.suppressPreviewableAsyncWarning) {
                    console.warn(
                        `${action.id} is previewable => apply or clean should not be async.`
                    );
                }
            }
        }
        return Promise.all(proms);
    }

    /**
     * TODO
     * @param applySpecs
     * @param dependencyManager
     * @param selectableContext
     * @param isPreviewing
     * @param {boolean|function} apply
     * @param defaultToApply
     * @param nextApplySpecs
     * @returns {Promise<Awaited<unknown>[]>}
     */
    async callApplySpecs(
        applySpecs,
        dependencyManager,
        selectableContext,
        isPreviewing,
        apply = true,
        defaultToApply = true,
        nextApplySpecs = undefined
    ) {
        return this._forEachApplySpec(applySpecs, isPreviewing, (applySpec) => {
            const isApply = typeof apply === "function" ? apply(applySpec) : apply;
            let methodToCall = isApply ? applySpec.apply : applySpec.clean;
            const isDefaultedToApply = !isApply && !methodToCall && defaultToApply;
            if (isDefaultedToApply) {
                methodToCall = applySpec.apply;
            }

            const hasLoadResult = isApply || isDefaultedToApply || applySpec.loadOnClean;
            let nextAction;
            return methodToCall?.({
                editingElement: applySpec.editingElement,
                params: applySpec.actionParam,
                value: applySpec.actionValue,
                loadResult: hasLoadResult ? applySpec.loadResult : null,
                dependencyManager,
                selectableContext,
                isPreviewing,
                get nextAction() {
                    if (!nextApplySpecs) {
                        return undefined;
                    }
                    nextAction =
                        nextAction ||
                        nextApplySpecs.find((a) => a.actionId === applySpec.actionId) ||
                        {};
                    return {
                        params: nextAction.actionParam,
                        value: nextAction.actionValue,
                    };
                },
            });
        });
    }
}
