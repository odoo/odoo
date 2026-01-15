import { convertParamToObject } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

export class CompositeActionPlugin extends Plugin {
    static id = "compositeAction";
    static dependencies = ["builderActions"];

    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_actions: {
            CompositeAction,
            // Do not use with actions that need a custom reload.
            // TODO: a class approach to actions would be able to solve that
            // limitation and would also remove the need to split
            // `composite` and `reloadComposite`.
            ReloadCompositeAction,
        },
    };
}

export class CompositeAction extends BuilderAction {
    static id = "composite";
    static dependencies = ["builderActions"];
    loadOnClean = true;
    async prepare({ actionParam: { mainParam: actions }, actionValue }) {
        const proms = [];
        for (const actionDef of actions) {
            const action = this.dependencies.builderActions.getAction(actionDef.action);
            if (action.has("prepare")) {
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
    }
    getPriority({ params: { mainParam: actions }, value }) {
        const results = [];
        for (const actionDef of actions) {
            const action = this.dependencies.builderActions.getAction(actionDef.action);
            if (action.has("getPriority")) {
                const actionDescr = this._getActionDescription({ ...actionDef, value });
                results.push(action.getPriority(actionDescr));
            }
        }
        // TODO: should this be the max or a sum?
        return Math.max(...results);
    }
    // We arbitrarily keep the result of the 1st action, as we
    // obviously cannot return more than one value.
    getValue({ editingElement, params: { mainParam: actions } }) {
        let actionGetValue;
        const actionDef = actions.find((actionDef) => {
            const action = this.dependencies.builderActions.getAction(actionDef.action);
            if (action.has("getValue")) {
                actionGetValue = action.getValue;
            }
            return !!action.getValue;
        });
        if (actionDef) {
            const actionDescr = this._getActionDescription({
                editingElement,
                actionParam: actionDef.actionParam,
            });
            return actionGetValue(actionDescr);
        }
    }
    isApplied({ editingElement, params: { mainParam: actions }, value }) {
        const results = [];
        for (const actionDef of actions) {
            const action = this.dependencies.builderActions.getAction(actionDef.action);
            if (action.has("isApplied")) {
                const actionDescr = this._getActionDescription({
                    editingElement,
                    ...actionDef,
                    value,
                });
                results.push(action.isApplied(actionDescr));
            }
        }
        return !!results.length && results.every((result) => result);
    }
    async load({ editingElement, params: { mainParam: actions }, value }) {
        const loadActions = [];
        const loadResults = [];
        for (const actionDef of actions) {
            const action = this.dependencies.builderActions.getAction(actionDef.action);
            if (action.has("load")) {
                const actionDescr = this._getActionDescription({
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
    }
    async apply({
        editingElement,
        params: { mainParam: actions },
        value,
        loadResult,
        dependencyManager,
        selectableContext,
    }) {
        for (const actionDef of actions) {
            const action = this.dependencies.builderActions.getAction(actionDef.action);
            if (action.has("apply")) {
                const actionDescr = this._getActionDescription({
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
    }
    clean({
        editingElement,
        params: { mainParam: actions },
        value,
        loadResult,
        dependencyManager,
        selectableContext,
        nextAction,
    }) {
        for (const actionDef of actions) {
            const action = this.dependencies.builderActions.getAction(actionDef.action);
            const actionDescr = this._getActionDescription({
                editingElement,
                ...actionDef,
                value,
                loadResult,
                dependencyManager,
                selectableContext,
                nextAction,
            });
            if (action.has("clean")) {
                action.clean(actionDescr);
            } else if (action.has("apply")) {
                if (loadResult && loadResult[actionDef.action]) {
                    actionDescr.loadResult = loadResult[actionDef.action];
                }
                action.apply(actionDescr);
            }
        }
    }
    _getActionDescription(action) {
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

export class ReloadCompositeAction extends CompositeAction {
    static id = "reloadComposite";
    setup() {
        this.reload = {};
    }
}
