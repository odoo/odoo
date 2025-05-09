import { Plugin } from "@html_editor/plugin";

/**
 * @typedef {Object} BuilderAction
 * @property {string} id
 * @property {Function} apply
 * @property {Function} [isApplied]
 * @property {Function} [clean]
 * @property {() => Promise<any>} [load]
 */

export class BuilderActionsPlugin extends Plugin {
    static id = "builderActions";
    static shared = ["getAction", "applyAction"];
    static dependencies = ["operation", "history"];

    setup() {
        this.actions = {};
        for (const actions of this.getResource("builder_actions")) {
            for (const [actionId, action] of Object.entries(actions)) {
                if (actionId in this.actions) {
                    throw new Error(`Duplicate builder action id: ${actionId}`);
                }
                this.actions[actionId] = { id: actionId, ...action };
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
}
