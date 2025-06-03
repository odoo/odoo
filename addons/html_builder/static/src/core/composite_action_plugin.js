import { convertParamToObject } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";

export class CompositeActionPlugin extends Plugin {
    static id = "compositeAction";
    static dependencies = ["builderActions"];

    compositeAction = {
        prepare: async ({ actionParam: { mainParam: actions }, actionValue }) => {
            const proms = [];
            for (const actionDef of actions) {
                const action = this.dependencies.builderActions.getAction(actionDef.action);
                if (action.prepare) {
                    const actionDescr = { actionId: actionDef.action };
                    if (actionDef.actionParam) {
                        actionDescr.actionParam = convertParamToObject(actionDef.actionParam);
                    }
                    if (actionDef.actionValue || actionValue) {
                        actionDescr.actionValue = actionDef.actionValue || actionValue;
                    }
                    proms.push(action.prepare(actionDescr));
                }
            }
            await Promise.all(proms);
        },
        getPriority: ({ params: { mainParam: actions }, value }) => {
            const results = [];
            for (const actionDef of actions) {
                const action = this.dependencies.builderActions.getAction(actionDef.action);
                if (action.getPriority) {
                    const actionDescr = this.getActionDescription({ ...actionDef, value });
                    results.push(action.getPriority(actionDescr));
                }
            }
            // TODO: should this be the max or a sum?
            return Math.max(...results);
        },
        // We arbitrarily keep the result of the 1st action, as we
        // obviously cannot return more than one value.
        getValue: ({ editingElement, params: { mainParam: actions } }) => {
            let actionGetValue;
            const actionDef = actions.find((actionDef) => {
                const action = this.dependencies.builderActions.getAction(actionDef.action);
                if (action.getValue) {
                    actionGetValue = action.getValue;
                }
                return !!action.getValue;
            });
            if (actionDef) {
                const actionDescr = this.getActionDescription({
                    editingElement,
                    actionParam: actionDef.actionParam,
                });
                return actionGetValue(actionDescr);
            }
        },
        isApplied: ({ editingElement, params: { mainParam: actions }, value }) => {
            const results = [];
            for (const actionDef of actions) {
                const action = this.dependencies.builderActions.getAction(actionDef.action);
                if (action.isApplied) {
                    const actionDescr = this.getActionDescription({
                        editingElement,
                        ...actionDef,
                        value,
                    });
                    results.push(action.isApplied(actionDescr));
                }
            }
            return !!results.length && results.every((result) => result);
        },
        load: async ({ editingElement, params: { mainParam: actions }, value }) => {
            const loadActions = [];
            const loadResults = [];
            for (const actionDef of actions) {
                const action = this.dependencies.builderActions.getAction(actionDef.action);
                if (action.load) {
                    const actionDescr = this.getActionDescription({
                        editingElement,
                        ...actionDef,
                        value,
                    });
                    loadActions.push(actionDef.action);
                    // We can't use Promise.all as unrelated loads could have
                    // overriding impacts (like updating/creating the same file)
                    // In such cases, this approach allows to define the order
                    // of actions and ensures predictable load results.
                    loadResults.push(await action.load(actionDescr));
                }
            }
            return loadActions.reduce((acc, actionId, idx) => {
                acc[actionId] = loadResults[idx];
                return acc;
            }, {});
        },
        apply: async ({
            editingElement,
            params: { mainParam: actions },
            value,
            loadResult,
            dependencyManager,
            selectableContext,
        }) => {
            for (const actionDef of actions) {
                const action = this.dependencies.builderActions.getAction(actionDef.action);
                if (action.apply) {
                    const actionDescr = this.getActionDescription({
                        editingElement,
                        value,
                        ...actionDef,
                        loadResult,
                        dependencyManager,
                        selectableContext,
                    });
                    await action.apply(actionDescr);
                }
            }
        },
        loadOnClean: true,
        clean: ({
            editingElement,
            params: { mainParam: actions },
            value,
            loadResult,
            dependencyManager,
            selectableContext,
            nextAction,
        }) => {
            for (const actionDef of actions) {
                const action = this.dependencies.builderActions.getAction(actionDef.action);
                const actionDescr = this.getActionDescription({
                    editingElement,
                    ...actionDef,
                    value,
                    loadResult,
                    dependencyManager,
                    selectableContext,
                    nextAction,
                });

                if (action.clean) {
                    action.clean(actionDescr);
                } else if (action.apply) {
                    if (loadResult && loadResult[actionDef.action]) {
                        actionDescr.loadResult = loadResult[actionDef.action];
                    }
                    action.apply(actionDescr);
                }
            }
        },
    };

    resources = {
        builder_actions: {
            composite: this.compositeAction,
            reloadComposite: {
                // Do not use with actions that need a custom reload.
                // TODO: a class approach to actions would be able to solve that
                // limitation and would also remove the need to split
                // `composite` and `reloadComposite`.
                reload: {},
                ...this.compositeAction,
            },
        },
    };

    getActionDescription(action) {
        const { action: actionId, actionParam, actionValue, value, loadResult } = action;
        const actionDescr = {};
        const forwardedSpecs = [
            "editingElement",
            "dependencyManager",
            "selectableContext",
            "nextAction",
        ];
        for (const spec of forwardedSpecs) {
            if (action[spec]) {
                actionDescr[spec] = action[spec];
            }
        }
        if (actionParam) {
            actionDescr.params = convertParamToObject(actionParam);
        }
        if (actionValue || value) {
            actionDescr.value = actionValue || value;
        }
        if (loadResult && loadResult[actionId]) {
            actionDescr.loadResult = loadResult[actionId];
        }
        return actionDescr;
    }
}
