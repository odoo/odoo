import { convertParamToObject, isActionPreviewable } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

export class CompositeActionPlugin extends Plugin {
    static id = "compositeAction";
    static dependencies = ["builderActions"];

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

    suppressPreviewableAsyncWarning = true;
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
    async load({ isPreviewing, editingElement, params: { mainParam: actions }, value }) {
        const loadActions = [];
        const loadResults = [];
        for (const actionDef of actions) {
            const action = this.dependencies.builderActions.getAction(actionDef.action);
            if (action.has("load") && (!isPreviewing || isActionPreviewable(action))) {
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
        isPreviewing,
        editingElement,
        params: { mainParam: actions },
        value,
        loadResult,
        dependencyManager,
        selectableContext,
    }) {
        return this.dependencies.builderActions.callSpecs(
            this._getSpecsToCall(true, {
                isPreviewing,
                editingElement,
                loadResult,
                actions,
                value,
            }),
            dependencyManager,
            selectableContext,
            isPreviewing
        );
    }

    async clean({
        isPreviewing,
        editingElement,
        params: { mainParam: actions },
        value,
        loadResult,
        dependencyManager,
        selectableContext,
        nextAction,
    }) {
        return this.dependencies.builderActions.callSpecs(
            this._getSpecsToCall(false, {
                isPreviewing,
                editingElement,
                loadResult,
                actions,
                value,
            }),
            dependencyManager,
            selectableContext,
            isPreviewing,
            () => false,
            true,
            [nextAction]
        );
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

    _getActionSpec(action) {
        const { editingElement, params, value, loadResult, nextAction } =
            this._getActionDescription(action);

        const spec = {
            actionId: action.action,
            editingElement,
            actionParam: params,
            actionValue: value,
            loadResult,
            nextAction,
        };
        const overridableMethods = ["apply", "clean", "load", "loadOnClean"];
        for (const method of overridableMethods) {
            if (!action.has || action.has(method)) {
                spec[method] = action[method];
            }
        }
        return spec;
    }

    _getSpecsToCall(
        isApply,
        { isPreviewing, editingElement, loadResult, actions, value, nextAction }
    ) {
        const allSpecs = this.dependencies.builderActions.getActionsSpecs(
            actions.map((actionDef) => ({
                actionId: actionDef.action,
                actionParam: convertParamToObject(actionDef.actionParam),
                actionValue: actionDef.actionValue || value,
            })),
            [editingElement]
        );
        const specsToCall = [];
        for (const spec of allSpecs) {
            if (
                (!isApply || spec.action.has("apply")) &&
                (!isPreviewing || isActionPreviewable(spec.action))
            ) {
                specsToCall.push({
                    ...spec,
                    loadResult: loadResult ? loadResult[spec.actionId] : undefined,
                    nextAction,
                });
            }
        }
        return specsToCall;
    }
}

export class ReloadCompositeAction extends CompositeAction {
    static id = "reloadComposite";
    setup() {
        this.reload = {
            previewable: true,
        };
    }
}
