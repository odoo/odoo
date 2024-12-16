import { isTextNode } from "@html_editor/utils/dom_info";
import {
    Component,
    onWillDestroy,
    useComponent,
    useEffect,
    useEnv,
    useRef,
    useState,
    useSubEnv,
    xml,
} from "@odoo/owl";
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
        dependencies: { type: [String, { type: Array, element: String }], optional: true },
        slots: { type: Object },
    };

    setup() {
        const isDependenciesVisible = useDependencies(this.props.dependencies);
        const isVisible = () =>
            !!this.env.getEditingElement() && (!this.props.dependencies || isDependenciesVisible());
        this.state = useDomState(() => ({
            isVisible: isVisible(),
        }));
        if (this.props.dependencies?.length) {
            const listener = () => {
                this.state.isVisible = isVisible();
            };
            this.env.dependencyManager.addEventListener("dependency-added", listener);
            onWillDestroy(() => {
                this.env.dependencyManager.removeEventListener("dependency-added", listener);
            });
        }
    }
}

function querySelectorAll(targets, selector) {
    const elements = new Set();
    for (const target of targets) {
        for (const el of target.querySelectorAll(selector)) {
            elements.add(el);
        }
    }
    return [...elements];
}

export function useWeComponent() {
    const comp = useComponent();
    const newEnv = {};
    const oldEnv = useEnv();
    if (comp.props.applyTo) {
        let editingElements = querySelectorAll(oldEnv.getEditingElements(), comp.props.applyTo);
        useBus(oldEnv.editorBus, "UPDATE_EDITING_ELEMENT", () => {
            editingElements = querySelectorAll(oldEnv.getEditingElements(), comp.props.applyTo);
        });
        newEnv.getEditingElements = () => editingElements;
        newEnv.getEditingElement = () => editingElements[0];
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
export function useDependecyDefinition({ id, isActive }) {
    const comp = useComponent();
    comp.env.dependencyManager.add(id, isActive);
    onWillDestroy(() => {
        comp.env.dependencyManager.removeByValue(isActive);
    });
}

export function useDependencies(dependencies) {
    const env = useEnv();
    const isDependenciesVisible = () => {
        const deps = Array.isArray(dependencies) ? dependencies : [dependencies];
        return deps.filter(Boolean).every((dependencyId) => {
            const match = dependencyId.match(/(!)?(.*)/);
            const inverse = !!match[1];
            const id = match[2];
            const isActiveFn = env.dependencyManager.get(id);
            if (!isActiveFn) {
                return false;
            }
            const isActive = isActiveFn();
            return inverse ? !isActive : isActive;
        });
    };
    return isDependenciesVisible;
}

export function useClickableWeWidget() {
    useWeComponent();
    const comp = useComponent();
    const getAction = comp.env.editor.shared.builderActions.getAction;
    const applyOperation = comp.env.editor.shared.history.makePreviewableOperation(callApply);
    const shouldToggle = !comp.env.actionBus;

    const operation = {
        commit: () => {
            callOperation(applyOperation.commit);
        },
        preview: () => {
            callOperation(applyOperation.preview, {
                cancellable: true,
                cancelPrevious: () => applyOperation.revert(),
            });
        },
        revert: () => {
            // The `next` will cancel the previous operation, which will revert
            // the operation in case of a preview.
            comp.env.editor.shared.operation.next();
        },
    };

    if (
        comp.props.preview === false ||
        (comp.env.weContext.preview === false && comp.props.preview !== true)
    ) {
        operation.preview = () => {};
    }

    const state = useDomState(() => ({
        isActive: isActive(),
    }));

    if (comp.env.actionBus) {
        useBus(comp.env.actionBus, "BEFORE_CALL_ACTIONS", () => {
            for (const { actionId, actionParam, actionValue } of getAllActions()) {
                for (const editingElement of comp.env.getEditingElements()) {
                    getAction(actionId).clean?.({
                        editingElement,
                        param: actionParam,
                        value: actionValue,
                    });
                }
            }
        });
    }

    function callOperation(fn, operationParams) {
        const actionsSpecs = getActionsSpecs(getAllActions());
        comp.env.editor.shared.operation.next(
            () => {
                fn(actionsSpecs);
            },
            {
                load: async () =>
                    Promise.all(
                        actionsSpecs.map(async (applySpec) => {
                            if (!applySpec.load) {
                                return;
                            }
                            const result = await applySpec.load({
                                editingElement: applySpec.editingElement,
                                param: applySpec.actionParam,
                                value: applySpec.actionValue,
                            });
                            applySpec.loadResult = result;
                        })
                    ),
                ...operationParams,
            }
        );
    }
    function getActionsSpecs(actions) {
        const specs = [];
        for (const { actionId, actionParam, actionValue } of actions) {
            const action = getAction(actionId);
            for (const editingElement of comp.env.getEditingElements()) {
                specs.push({
                    editingElement,
                    actionId,
                    actionParam,
                    actionValue,
                    apply: action.apply,
                    clean: action.clean,
                    load: action.load,
                });
            }
        }
        return specs;
    }
    function callApply(applySpecs) {
        comp.env.actionBus?.trigger("BEFORE_CALL_ACTIONS");
        const shouldClean = shouldToggle && isActive();
        for (const applySpec of applySpecs) {
            if (shouldClean) {
                applySpec.clean({
                    editingElement: applySpec.editingElement,
                    param: applySpec.actionParam,
                    value: applySpec.actionValue,
                });
            } else {
                applySpec.apply({
                    editingElement: applySpec.editingElement,
                    param: applySpec.actionParam,
                    value: applySpec.actionValue,
                    loadResult: applySpec.loadResult,
                });
            }
        }
    }

    function getShorthandActions() {
        const actions = [];
        const shorthands = [
            ["classAction", "classActionValue"],
            ["attributeAction", "attributeActionValue"],
            ["dataAttributeAction", "dataAttributeActionValue"],
            ["styleAction", "styleActionValue"],
        ];
        for (const [actionId, actionValue] of shorthands) {
            const actionParam = comp.env.weContext[actionId] || comp.props[actionId];
            if (actionParam) {
                actions.push({ actionId, actionParam, actionValue: comp.props[actionValue] });
            }
        }
        return actions;
    }
    function getCustomAction() {
        const action = {
            actionId: comp.env.weContext.action || comp.props.action,
            actionParam: comp.env.weContext.actionParam || comp.props.actionParam,
            actionValue: comp.props.actionValue,
        };
        if (action.actionId) {
            return action;
        }
    }
    function getAllActions() {
        const actions = getShorthandActions();

        const { actionId, actionParam, actionValue } = getCustomAction() || {};
        if (actionId) {
            actions.push({ actionId, actionParam, actionValue });
        }
        return actions;
    }
    function isActive() {
        const editingElements = comp.env.getEditingElements();
        if (!editingElements.length) {
            return;
        }
        return getAllActions().every((o) => {
            const { actionId, actionParam, actionValue } = o;
            // TODO isActive === first editing el or all ?
            const editingElement = editingElements[0];
            return getAction(actionId).isActive?.({
                editingElement,
                param: actionParam,
                value: actionValue,
            });
        });
    }

    return {
        state,
        operation,
        isActive,
    };
}
export function useInputWeWidget() {
    const comp = useComponent();
    const getAction = comp.env.editor.shared.builderActions.getAction;
    const state = useDomState(getState);
    const applyValue = comp.env.editor.shared.history.makePreviewableOperation((value) => {
        for (const [actionId, actionParam] of getActions()) {
            for (const editingElement of comp.env.getEditingElements()) {
                getAction(actionId).apply({
                    editingElement,
                    param: actionParam,
                    value,
                });
            }
        }
    });
    function getState(editingElement) {
        if (!editingElement) {
            // TODO try to remove it. We need to move hook in WeComponent
            return {};
        }
        const [actionId, actionParam] = getActions()[0];
        return {
            value: getAction(actionId).getValue({
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

export function useApplyVisibility(refName) {
    const ref = useRef(refName);
    return (hasContent) => {
        ref.el?.classList.toggle("d-none", !hasContent);
    };
}

export function useVisibilityObserver(contentName, callback) {
    const contentRef = useRef(contentName);

    const applyVisibility = () => {
        const hasContent = [...contentRef.el.childNodes].some((el) =>
            isTextNode(el) ? el.textContent !== "" : !el.classList.contains("d-none")
        );
        callback(hasContent);
    };

    const observer = new MutationObserver(applyVisibility);
    useEffect(
        (contentEl) => {
            if (!contentEl) {
                return;
            }
            applyVisibility();
            observer.observe(contentEl, {
                subtree: true,
                attributes: true,
                childList: true,
                attributeFilter: ["class"],
            });
            return () => {
                observer.disconnect();
            };
        },
        () => [contentRef.el]
    );
}

export const basicContainerWeWidgetProps = {
    applyTo: { type: String, optional: true },
    preview: { type: Boolean, optional: true },
    dependencies: { type: [String, Array], optional: true },
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
