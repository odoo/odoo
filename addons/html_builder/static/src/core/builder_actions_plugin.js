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
    static shared = ["getAction", "applyAction", "callSpecs", "getActionsSpecs"];
    static dependencies = ["operation", "history"];
    setup() {
        this.actions = {};
        for (const actions of this.getResource("builder_actions")) {
            for (const Action of Object.values(actions)) {
                if (Action.id in this.actions) {
                    throw new Error(`Duplicate builder action id: ${Action.id}`);
                }
                const deps = {};
                for (const depName of Action.dependencies) {
                    deps[depName] = this.config.getShared()[depName];
                }
                this.actions[Action.id] = new Action(this, deps);
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

    getActionsSpecs(actions, editingElements, userInputValue = undefined) {
        const specs = [];
        for (let { actionId, actionParam, actionValue } of actions) {
            const action = this.getAction(actionId);
            // Take the action value defined by the clickable or the input given
            // by the user.
            actionValue = actionValue === undefined ? userInputValue : actionValue;
            for (const editingElement of editingElements) {
                specs.push({
                    editingElement,
                    actionId,
                    actionParam,
                    actionValue,
                    action,
                });
            }
        }
        return specs;
    }

    /**
     * Call apply or clean for each spec in {@link specs}.
     *
     * @typedef {Object} ActionCallSpec
     *
     * @param {[ActionCallSpec]} specs
     * @param dependencyManager
     * @param selectableContext
     * @param {boolean} isPreviewing
     * @param {function(ActionCallSpec): boolean} [isApply=true]
     *   `true`: call apply.
     *   `false`: call clean if it exists. See {@link defaultToApply}.
     * @param {boolean} [defaultToApply=true] - true: if apply is false and spec.clean doesn't exist, fallback to spec.apply.
     * @param {[any]} [nextApplySpecs]
     * @returns {Promise<Awaited<unknown>[]>}
     */
    async callSpecs(
        specs,
        dependencyManager,
        selectableContext,
        isPreviewing,
        isApply = (spec) => true,
        defaultToApply = true,
        nextApplySpecs = undefined
    ) {
        return this._callAllSpecs(specs, isPreviewing, (spec) => {
            let methodToCall = isApply(spec) ? "apply" : "clean";
            if (!spec.action.has(methodToCall) && defaultToApply) {
                methodToCall = "apply";
            }

            let nextAction;
            return spec.action[methodToCall]?.({
                isPreviewing,
                editingElement: spec.editingElement,
                params: spec.actionParam,
                value: spec.actionValue,
                loadResult:
                    methodToCall === "apply" || spec.action.loadOnClean ? spec.loadResult : null,
                dependencyManager,
                selectableContext,
                get nextAction() {
                    if (!nextApplySpecs) {
                        return undefined;
                    }
                    nextAction =
                        nextAction ||
                        nextApplySpecs.find((a) => a.actionId === spec.actionId) ||
                        {};
                    return {
                        params: nextAction.actionParam,
                        value: nextAction.actionValue,
                    };
                },
            });
        });
    }

    async _callAllSpecs(specs, isPreviewing, callback) {
        const proms = [];
        for (const spec of specs) {
            const result = callback(spec);
            proms.push(result);

            // If result is a promise, this means apply or clean is async. If we're previewing, this is bad practice.
            // We discourage this practice with a warning.
            const isPromise = typeof result?.then === "function";
            if (isPreviewing && isPromise && !spec.action.suppressPreviewableAsyncWarning) {
                console.warn(
                    `${spec.actionId} is previewable => apply or clean should not be async.`
                );
            }
        }
        return Promise.all(proms);
    }
}
