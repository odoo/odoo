import { Component, onWillUpdateProps, useComponent, useState, useSubEnv, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";

export function useDomState(getState) {
    const state = useState(getState());
    const component = useComponent();
    useBus(component.env.editorBus, "STEP_ADDED", () => {
        Object.assign(state, getState());
    });
    return state;
}

export class WithSubEnv extends Component {
    static template = xml`<t t-slot="default" />`;
    static props = {
        env: Object,
        slots: Object,
    };

    setup() {
        useSubEnv(this.props.env);
    }
}

export function useWeComponent() {
    const comp = useComponent();
    const newEnv = {};
    if (comp.props.applyTo) {
        newEnv.editingElement = comp.env.editingElement.querySelector(comp.props.applyTo);
    }
    const weContext = {};
    const contextKeys = [
        "action",
        "actionParam",
        "classAction",
        "attributeAction",
        "dataAttributeAction",
        "styleAction",
    ];
    for (const key of contextKeys) {
        if (comp.props[key]) {
            weContext[key] = comp.props[key];
        }
    }
    if (Object.keys(weContext).length) {
        newEnv.weContext = { ...comp.env.weContext, ...weContext };
    }
    if (Object.keys(newEnv).length) {
        useSubEnv(newEnv);
    }
}

const actionsRegistry = registry.category("website-builder-actions");

export function useClickableWeWidget() {
    useWeComponent();
    const comp = useComponent();
    const call = comp.env.editor.shared.history.makePreviewableOperation(callActions);

    let actions;
    getActions();
    onWillUpdateProps(getActions);

    const state = useDomState(() => ({
        isActive: isActive(),
    }));

    if (comp.env.actionBus) {
        useBus(comp.env.actionBus, "BEFORE_CALL_ACTIONS", () => {
            for (const [actionId, actionParam, actionValue] of actions) {
                actionsRegistry.get(actionId).clean?.({
                    editingElement: comp.env.editingElement,
                    param: actionParam,
                    value: actionValue,
                });
            }
        });
    }

    function callActions() {
        comp.env.actionBus?.trigger("BEFORE_CALL_ACTIONS");
        for (const [actionId, actionParam, actionValue] of actions) {
            actionsRegistry.get(actionId).apply({
                editingElement: comp.env.editingElement,
                param: actionParam,
                value: actionValue,
            });
        }
    }
    function getActions() {
        actions = [];
        const classAction = comp.env.weContext.classAction || comp.props.classAction;
        if (classAction) {
            actions.push(["classAction", classAction, comp.props.classActionValue]);
        }
        const attributeAction = comp.env.weContext.attributeAction || comp.props.attributeAction;
        if (attributeAction) {
            actions.push(["attributeAction", attributeAction, comp.props.attributeActionValue]);
        }
        const dataAttributeAction =
            comp.env.weContext.dataAttributeAction || comp.props.dataAttributeAction;
        if (dataAttributeAction) {
            actions.push([
                "dataAttributeAction",
                dataAttributeAction,
                comp.props.dataAttributeActionValue,
            ]);
        }
        const styleAction = comp.env.weContext.styleAction || comp.props.styleAction;
        if (styleAction) {
            actions.push(["styleAction", styleAction, comp.props.styleActionValue]);
        }
        const action = comp.env.weContext.action || comp.props.action;
        const actionParam = comp.env.weContext.actionParam || comp.props.actionParam;
        if (action) {
            actions.push([action, actionParam, comp.props.actionValue]);
        }
    }
    function isActive() {
        return actions.every(([actionId, actionParam, actionValue]) => {
            return actionsRegistry.get(actionId).isActive?.({
                editingElement: comp.env.editingElement,
                param: actionParam,
                value: actionValue,
            });
        });
    }

    return {
        state,
        call,
    };
}

export const basicContainerWeWidgetProps = {
    applyTo: { type: String, optional: true },
    // preview: { type: Boolean, optional: true },
    // reloadPage: { type: Boolean, optional: true },

    action: { type: String, optional: true },
    actionParam: { validate: () => true, optional: true },

    // Shorthand actions.
    classAction: { type: String, optional: true },
    attributeAction: { type: String, optional: true },
    dataAttributeAction: { type: String, optional: true },
    styleAction: { type: String, optional: true },
};
export const clickableWeWidgetProps = {
    ...basicContainerWeWidgetProps,

    actionValue: {
        type: [Boolean, String, Number, { type: Array, element: [Boolean, String, Number] }],
        optional: true,
    },

    // Shorthand actions values.
    classActionValue: { type: [String, Array], optional: true },
    attributeActionValue: { type: [String, Array], optional: true },
    dataAttributeActionValue: { type: [String, Array], optional: true },
    styleActionValue: { type: [String, Array], optional: true },
};
