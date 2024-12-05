import { Component, useComponent, useEnv, useState, useSubEnv, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";

export function useDomState(getState) {
    const env = useEnv();
    const state = useState(getState(env.getEditingElement()));
    useBus(env.editorBus, "STEP_ADDED", () => {
        Object.assign(state, getState(env.getEditingElement()));
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

export class WeComponent extends Component {
    static template = xml`<t t-if="this.state.isVisible"><t t-slot="default"/></t>`;
    static props = {
        slots: { type: Object },
    };

    setup() {
        this.state = useDomState((editingElement) => {
            return {
                isVisible: !!editingElement,
            };
        });
    }
}

export function useWeComponent() {
    const comp = useComponent();
    const newEnv = {};
    const oldEnv = useEnv();
    if (comp.props.applyTo) {
        let editingElement = oldEnv.getEditingElement().querySelector(comp.props.applyTo);
        useBus(oldEnv.editorBus, "UPDATE_EDITING_ELEMENT", () => {
            editingElement = oldEnv.getEditingElement().querySelector(comp.props.applyTo);
        });
        newEnv.getEditingElement = () => {
            return editingElement;
        };
    }
    const weContext = {};
    const contextKeys = [
        "preview",
        "action",
        "actionParam",
        "classAction",
        "attributeAction",
        "dataAttributeAction",
        "styleAction",
    ];
    for (const key of contextKeys) {
        if (key in comp.props) {
            weContext[key] = comp.props[key];
        }
    }
    if (Object.keys(weContext).length) {
        newEnv.weContext = { ...comp.env.weContext, ...weContext };
    }
    useSubEnv(newEnv);
}

const actionsRegistry = registry.category("website-builder-actions");

export function useClickableWeWidget() {
    useWeComponent();
    const comp = useComponent();
    const call = comp.env.editor.shared.history.makePreviewableOperation(callActions);
    if (
        comp.props.preview === false ||
        (comp.env.weContext.preview === false && comp.props.preview !== true)
    ) {
        call.preview = () => {};
    }

    const state = useDomState(() => ({
        isActive: isActive(),
    }));

    if (comp.env.actionBus) {
        useBus(comp.env.actionBus, "BEFORE_CALL_ACTIONS", () => {
            for (const [actionId, actionParam, actionValue] of getActions()) {
                actionsRegistry.get(actionId).clean?.({
                    editingElement: comp.env.getEditingElement(),
                    param: actionParam,
                    value: actionValue,
                });
            }
        });
    }

    function callActions() {
        comp.env.actionBus?.trigger("BEFORE_CALL_ACTIONS");
        for (const [actionId, actionParam, actionValue] of getActions()) {
            actionsRegistry.get(actionId).apply({
                editingElement: comp.env.getEditingElement(),
                param: actionParam,
                value: actionValue,
            });
        }
    }
    function getActions() {
        const actions = [];

        const shorthands = [
            ["classAction", "classActionValue"],
            ["attributeAction", "attributeActionValue"],
            ["dataAttributeAction", "dataAttributeActionValue"],
            ["styleAction", "styleActionValue"],
        ];
        for (const [actionName, actionValue] of shorthands) {
            const value = comp.env.weContext[actionName] || comp.props[actionName];
            if (value) {
                actions.push([actionName, value, comp.props[actionValue]]);
            }
        }

        const action = comp.env.weContext.action || comp.props.action;
        const actionParam = comp.env.weContext.actionParam || comp.props.actionParam;
        if (action) {
            actions.push([action, actionParam, comp.props.actionValue]);
        }
        return actions;
    }
    function isActive() {
        const editingElement = comp.env.getEditingElement();
        if (!editingElement) {
            return;
        }
        return getActions().every(([actionId, actionParam, actionValue]) => {
            return actionsRegistry.get(actionId).isActive?.({
                editingElement,
                param: actionParam,
                value: actionValue,
            });
        });
    }

    return {
        state,
        call,
        isActive,
    };
}
export function useInputWeWidget() {
    const comp = useComponent();
    const state = useDomState(getState);
    const applyValue = comp.env.editor.shared.history.makePreviewableOperation((value) => {
        for (const [actionId, actionParam] of getActions()) {
            actionsRegistry.get(actionId).apply({
                editingElement: comp.env.getEditingElement(),
                param: actionParam,
                value,
            });
        }
    });
    function getState(editingElement) {
        if (!editingElement) {
            // TODO try to remove it. We need to move hook in WeComponent
            return {};
        }
        const [actionId, actionParam] = getActions()[0];
        return {
            value: actionsRegistry.get(actionId).getValue({
                editingElement,
                param: actionParam,
            }),
        };
    }
    function getActions() {
        const actions = [];
        const actionNames = [
            "classAction",
            "attributeAction",
            "dataAttributeAction",
            "styleAction",
        ];
        for (const actionName of actionNames) {
            if (comp.props[actionName]) {
                actions.push([actionName, comp.props[actionName]]);
            }
        }

        if (comp.props.action) {
            actions.push([comp.props.action, comp.props.actionParam]);
        }
        return actions;
    }
    let lastCommitedValue;
    function onChange(e) {
        const value = e.target.value;
        if (value === lastCommitedValue) {
            return;
        }
        lastCommitedValue = value;
        applyValue.commit(value);
    }
    function onInput(e) {
        applyValue.preview(e.target.value);
    }
    return {
        state,
        onChange,
        onInput,
    };
}

export const basicContainerWeWidgetProps = {
    applyTo: { type: String, optional: true },
    preview: { type: Boolean, optional: true },
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
const validateIsNull = { validate: (value) => value === null };
export const clickableWeWidgetProps = {
    ...basicContainerWeWidgetProps,

    actionValue: {
        type: [Boolean, String, Number, { type: Array, element: [Boolean, String, Number] }],
        optional: true,
    },

    // Shorthand actions values.
    classActionValue: { type: [String, Array, validateIsNull], optional: true },
    attributeActionValue: { type: [String, Array, validateIsNull], optional: true },
    dataAttributeActionValue: { type: [String, Array, validateIsNull], optional: true },
    styleActionValue: { type: [String, Array, validateIsNull], optional: true },
};
