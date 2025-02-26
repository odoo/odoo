import { isTextNode } from "@html_editor/utils/dom_info";
import { convertNumericToUnit } from "@html_editor/utils/formatting";
import {
    onMounted,
    onWillDestroy,
    useComponent,
    useEffect,
    useEnv,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export function useDomState(getState) {
    const env = useEnv();
    const state = useState(getState(env.getEditingElement()));
    useBus(env.editorBus, "DOM_UPDATED", () => {
        const editingElement = env.getEditingElement();
        if (!editingElement || editingElement.isConnected) {
            Object.assign(state, getState(editingElement));
        }
    });
    return state;
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

export function useBuilderComponent() {
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
    for (const key in basicContainerBuilderComponentProps) {
        if (key in comp.props) {
            weContext[key] = comp.props[key];
        }
    }
    if (Object.keys(weContext).length) {
        newEnv.weContext = { ...comp.env.weContext, ...weContext };
    }
    useSubEnv(newEnv);
}
export function useDependencyDefinition(id, item) {
    const comp = useComponent();
    comp.env.dependencyManager.add(id, item);
    onWillDestroy(() => {
        comp.env.dependencyManager.removeByValue(item);
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
            const isActiveFn = env.dependencyManager.get(id)?.isActive;
            if (!isActiveFn) {
                return false;
            }
            const isActive = isActiveFn();
            return inverse ? !isActive : isActive;
        });
    };
    return isDependenciesVisible;
}

export function useIsActiveItem() {
    const env = useEnv();
    const listenedKeys = new Set();

    function isActive(itemId) {
        const isActiveFn = env.dependencyManager.get(itemId)?.isActive;
        if (!isActiveFn) {
            return false;
        }
        return isActiveFn();
    }

    const getState = () => {
        const newState = {};
        for (const itemId of listenedKeys) {
            newState[itemId] = isActive(itemId);
        }
        return newState;
    };
    const state = useDomState(getState);
    const listener = () => {
        const newState = getState();
        Object.assign(state, newState);
    };
    env.dependencyManager.addEventListener("dependency-updated", listener);
    onWillDestroy(() => {
        env.dependencyManager.removeEventListener("dependency-updated", listener);
    });
    return function isActiveItem(itemId) {
        listenedKeys.add(itemId);
        if (state[itemId] === undefined) {
            return isActive(itemId);
        }
        return state[itemId];
    };
}

export function useGetItemValue() {
    const env = useEnv();
    const listenedKeys = new Set();

    function getValue(itemId) {
        const getValueFn = env.dependencyManager.get(itemId)?.getValue;
        if (!getValueFn) {
            return null;
        }
        return getValueFn();
    }

    const getState = () => {
        const newState = {};
        for (const itemId of listenedKeys) {
            newState[itemId] = getValue(itemId);
        }
        return newState;
    };
    const state = useDomState(getState);
    const listener = () => {
        const newState = getState();
        Object.assign(state, newState);
    };
    env.dependencyManager.addEventListener("dependency-updated", listener);
    onWillDestroy(() => {
        env.dependencyManager.removeEventListener("dependency-updated", listener);
    });
    return function getItemValue(itemId) {
        listenedKeys.add(itemId);
        if (state[itemId] === undefined) {
            return getValue(itemId);
        }
        return state[itemId];
    };
}

export function useSelectableComponent(id, { onItemChange } = {}) {
    useBuilderComponent();
    const selectableItems = [];
    const refreshCurrentItemDebounced = useDebounced(refreshCurrentItem, 0, { immediate: true });
    let currentSelectedItem;
    const env = useEnv();

    function refreshCurrentItem() {
        let currentItem;
        let itemPriority = 0;
        for (const selectableItem of selectableItems) {
            if (selectableItem.isApplied() && selectableItem.priority >= itemPriority) {
                currentItem = selectableItem;
                itemPriority = selectableItem.priority;
            }
        }
        if (currentItem && currentItem !== currentSelectedItem) {
            currentSelectedItem = currentItem;
            env.dependencyManager.triggerDependencyUpdated();
        }
        if (currentItem) {
            onItemChange?.(currentItem);
        }
    }

    if (id) {
        useDependencyDefinition(id, {
            type: "select",
            getSelectableItems: () => selectableItems.slice(0),
        });
    }

    onMounted(refreshCurrentItem);
    useBus(env.editorBus, "DOM_UPDATED", (ev) => {
        if (ev.detail.isPreviewing) {
            return;
        }
        refreshCurrentItem();
    });
    function cleanSelectedItem(...args) {
        if (currentSelectedItem) {
            currentSelectedItem.clean(...args);
        }
    }

    useSubEnv({
        selectableContext: {
            cleanSelectedItem,
            addSelectableItem: (item) => {
                selectableItems.push(item);
            },
            removeSelectableItem: (item) => {
                const index = selectableItems.indexOf(item);
                if (index !== -1) {
                    selectableItems.splice(index, 1);
                }
            },
            update: refreshCurrentItemDebounced,
            getSelectedItem: () => {
                refreshCurrentItem();
                return currentSelectedItem;
            },
        },
    });
}
export function useSelectableItemComponent(id, { getLabel = () => {} } = {}) {
    const { operation, isApplied, getActions, priority, clean } = useClickableBuilderComponent();
    const env = useEnv();

    let isSelectableActive = isApplied;
    if (env.selectableContext) {
        isSelectableActive = () => env.selectableContext.getSelectedItem() === selectableItem;

        const selectableItem = {
            isApplied,
            priority,
            getLabel,
            clean,
            getActions,
        };

        env.selectableContext.addSelectableItem(selectableItem);
        onMounted(env.selectableContext.update);
        onWillDestroy(() => {
            env.selectableContext.removeSelectableItem(selectableItem);
        });
    }

    if (id) {
        useDependencyDefinition(id, {
            isActive: isSelectableActive,
            getActions,
            onBeforeApplyAction: () => {},
            cleanSelectedItem: env.selectableContext?.cleanSelectedItem,
        });
    }

    const state = useDomState(() => ({
        isActive: isSelectableActive(),
    }));

    return { state, operation };
}
export function useClickableBuilderComponent() {
    useBuilderComponent();
    const comp = useComponent();
    const { getAllActions, callOperation, isApplied } = getAllActionsAndOperations(comp);
    const getAction = comp.env.editor.shared.builderActions.getAction;
    const applyOperation = comp.env.editor.shared.history.makePreviewableOperation(callApply);
    const shouldToggle = !comp.env.selectableContext;
    const inheritedActionIds =
        comp.props.inheritedActions || comp.env.weContext.inheritedActions || [];
    const hasPreview =
        comp.props.preview === true ||
        (comp.props.preview === undefined && comp.env.weContext.preview !== false);

    const operation = {
        commit: () => {
            callOperation(applyOperation.commit);
        },
        preview: () => {
            callOperation(applyOperation.preview, {
                operationParams: {
                    cancellable: true,
                    cancelPrevious: () => applyOperation.revert(),
                },
            });
        },
        revert: () => {
            // The `next` will cancel the previous operation, which will revert
            // the operation in case of a preview.
            comp.env.editor.shared.operation.next();
        },
    };

    if (!hasPreview) {
        operation.preview = () => {};
    }

    function clean(nextApplySpecs) {
        for (const { actionId, actionParam, actionValue } of getAllActions()) {
            for (const editingElement of comp.env.getEditingElements()) {
                let nextAction;
                getAction(actionId).clean?.({
                    editingElement,
                    param: actionParam,
                    value: actionValue,
                    dependencyManager: comp.env.dependencyManager,
                    get nextAction() {
                        nextAction =
                            nextAction || nextApplySpecs.find((a) => a.actionId === actionId) || {};
                        return {
                            param: nextAction.actionParam,
                            value: nextAction.actionValue,
                        };
                    },
                });
            }
        }
    }

    function callApply(applySpecs) {
        comp.env.selectableContext?.cleanSelectedItem(applySpecs);
        const cleans = inheritedActionIds
            .map((actionId) => comp.env.dependencyManager.get(actionId).cleanSelectedItem)
            .filter(Boolean);
        for (const clean of new Set(cleans)) {
            clean(applySpecs);
        }
        let shouldClean = shouldToggle && isApplied();
        shouldClean = comp.props.inverseAction ? !shouldClean : shouldClean;
        for (const applySpec of applySpecs) {
            if (shouldClean) {
                applySpec.clean?.({
                    editingElement: applySpec.editingElement,
                    param: applySpec.actionParam,
                    value: applySpec.actionValue,
                    dependencyManager: comp.env.dependencyManager,
                });
            } else {
                applySpec.apply({
                    editingElement: applySpec.editingElement,
                    param: applySpec.actionParam,
                    value: applySpec.actionValue,
                    loadResult: applySpec.loadResult,
                    dependencyManager: comp.env.dependencyManager,
                });
            }
        }
    }
    function getPriority() {
        return (
            getAllActions()
                .map(
                    (a) =>
                        getAction(a.actionId).getPriority?.({
                            param: a.actionParam,
                            value: a.actionValue,
                        }) || 0
                )
                .find((x) => x !== 0) || 0
        );
    }

    return {
        operation,
        isApplied,
        clean,
        priority: getPriority(),
        getActions: getAllActions,
    };
}
export function useInputBuilderComponent({
    id,
    defaultValue,
    formatRawValue = (rawValue) => rawValue,
    parseDisplayValue = (displayValue) => displayValue,
} = {}) {
    const comp = useComponent();
    // TODO: replace saveUnit and unit by formatRawValue and parseDisplayValue?
    if (comp.props.saveUnit && !comp.props.unit) {
        throw new Error("'unit' must be defined to use the 'saveUnit' props");
    }
    const { getAllActions, callOperation } = getAllActionsAndOperations(comp);
    const getAction = comp.env.editor.shared.builderActions.getAction;
    const state = useDomState(getState);
    const applyOperation = comp.env.editor.shared.history.makePreviewableOperation((applySpecs) => {
        for (const applySpec of applySpecs) {
            const actionValue =
                applySpec.actionValue === undefined
                    ? undefined
                    : applySpec.actionValue
                          .split(/\s+/g)
                          .map((singleValue) => {
                              if (comp.props.unit && comp.props.saveUnit) {
                                  // Convert value from unit to saveUnit
                                  singleValue = convertNumericToUnit(
                                      singleValue,
                                      comp.props.unit,
                                      comp.props.saveUnit
                                  );
                              }
                              if (comp.props.unit) {
                                  if (comp.props.saveUnit || comp.props.saveUnit === "") {
                                      singleValue = singleValue + comp.props.saveUnit;
                                  } else {
                                      singleValue = singleValue + comp.props.unit;
                                  }
                              }
                              return singleValue;
                          })
                          .join(" ");
            applySpec.apply({
                editingElement: applySpec.editingElement,
                param: applySpec.actionParam,
                value: actionValue,
                loadResult: applySpec.loadResult,
                dependencyManager: comp.env.dependencyManager,
            });
        }
    });
    function getState(editingElement) {
        if (!editingElement || !editingElement.isConnected) {
            // TODO try to remove it. We need to move hook in BuilderComponent
            return {};
        }
        const actionWithGetValue = getAllActions().find(
            ({ actionId }) => getAction(actionId).getValue
        );
        const { actionId, actionParam } = actionWithGetValue;
        let actionValue = getAction(actionId).getValue({ editingElement, param: actionParam });
        if (comp.props.unit && actionValue) {
            actionValue = actionValue
                .split(/\s+/g)
                .map((singleValue) => {
                    // Remove the unit
                    singleValue = singleValue.match(/\d+/g)[0];
                    if (comp.props.saveUnit) {
                        // Convert value from saveUnit to unit
                        singleValue = convertNumericToUnit(
                            singleValue,
                            comp.props.saveUnit,
                            comp.props.unit
                        );
                    }
                    return singleValue;
                })
                .join(" ");
        }
        return {
            value: actionValue,
        };
    }

    function commit(userInputValue) {
        if (defaultValue !== undefined) {
            userInputValue ||= formatRawValue(defaultValue);
        }
        const rawValue = parseDisplayValue(userInputValue);
        callOperation(applyOperation.commit, { userInputValue: rawValue });
        // If the parsed value is not equivalent to the user input, we want to
        // normalize the displayed value. It is useful in cases of invalid
        // input and allows to fall back to the output of parseDisplayValue.
        return rawValue !== undefined ? formatRawValue(rawValue) : "";
    }

    const shouldPreview =
        comp.props.preview !== false &&
        (comp.props.preview === true || comp.env.weContext.preview !== false);
    function preview(userInputValue) {
        if (shouldPreview) {
            callOperation(applyOperation.preview, {
                userInputValue: parseDisplayValue(userInputValue),
                operationParams: {
                    cancellable: true,
                    cancelPrevious: () => applyOperation.revert(),
                },
            });
        }
    }

    if (id) {
        useDependencyDefinition(id, {
            type: "input",
            getValue: () => state.value,
        });
    }

    return {
        state,
        commit,
        preview,
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

export const basicContainerBuilderComponentProps = {
    applyTo: { type: String, optional: true },
    preview: { type: Boolean, optional: true },
    inheritedActions: { type: Array, element: String, optional: true },
    // preview: { type: Boolean, optional: true },
    // reloadPage: { type: Boolean, optional: true },

    action: { type: String, optional: true },
    actionParam: { validate: () => true, optional: true },

    // Shorthand actions.
    classAction: { validate: () => true, optional: true },
    attributeAction: { validate: () => true, optional: true },
    dataAttributeAction: { validate: () => true, optional: true },
    styleAction: { validate: () => true, optional: true },
};
const validateIsNull = { validate: (value) => value === null };

export const clickableBuilderComponentProps = {
    ...basicContainerBuilderComponentProps,
    inverseAction: { type: Boolean, optional: true },

    actionValue: {
        type: [Boolean, String, Number, { type: Array, element: [Boolean, String, Number] }],
        optional: true,
    },

    // Shorthand actions values.
    classActionValue: { type: [String, Array, validateIsNull], optional: true },
    attributeActionValue: { type: [String, Array, validateIsNull], optional: true },
    dataAttributeActionValue: { type: [String, Array, validateIsNull], optional: true },
    styleActionValue: { type: [String, Array, validateIsNull], optional: true },

    inheritedActions: { type: Array, element: String, optional: true },
};

export function getAllActionsAndOperations(comp) {
    const inheritedActionIds =
        comp.props.inheritedActions || comp.env.weContext.inheritedActions || [];

    function getActionsSpecs(actions, userInputValue) {
        const getAction = comp.env.editor.shared.builderActions.getAction;
        const specs = [];
        for (let { actionId, actionParam, actionValue } of actions) {
            const action = getAction(actionId);
            // Take the action value defined by the clickable or the input given
            // by the user.
            actionValue = actionValue === undefined ? userInputValue : actionValue;
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
    function convertParamToObject(param) {
        if (param === undefined) {
            param = {};
        } else if (
            param instanceof Array ||
            param instanceof Function ||
            !(param instanceof Object)
        ) {
            param = {
                ["mainParam"]: param,
            };
        }
        return param;
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
            if (actionParam !== undefined) {
                actions.push({
                    actionId,
                    actionParam: convertParamToObject(actionParam),
                    actionValue: comp.props[actionValue],
                });
            }
        }
        return actions;
    }
    function getCustomAction() {
        const actionId = comp.props.action || comp.env.weContext.action;
        if (actionId) {
            const actionParam = comp.props.actionParam ?? comp.env.weContext.actionParam;
            return {
                actionId: actionId,
                actionParam: convertParamToObject(actionParam),
                actionValue: comp.props.actionValue,
            };
        }
    }
    function getAllActions() {
        const actions = getShorthandActions();

        const { actionId, actionParam, actionValue } = getCustomAction() || {};
        if (actionId) {
            actions.push({ actionId, actionParam, actionValue });
        }
        const inheritedActions =
            inheritedActionIds
                .map(
                    (actionId) =>
                        comp.env.dependencyManager
                            // The dependency might not be loaded yet.
                            .get(actionId)
                            ?.getActions?.() || []
                )
                .flat() || [];
        return actions.concat(inheritedActions || []);
    }
    function callOperation(fn, params = {}) {
        const actionsSpecs = getActionsSpecs(getAllActions(), params.userInputValue);
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
                            const shouldToggle = !comp.env.actionBus;
                            if (shouldToggle && isApplied()) {
                                // The element will be cleaned, do not load
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
                ...params.operationParams,
            }
        );
    }
    function isApplied() {
        const getAction = comp.env.editor.shared.builderActions.getAction;
        const editingElements = comp.env.getEditingElements();
        if (!editingElements.length) {
            return;
        }
        const areActionsActiveTabs = getAllActions().map((o) => {
            const { actionId, actionParam, actionValue } = o;
            // TODO isApplied === first editing el or all ?
            const editingElement = editingElements[0];
            const isApplied = getAction(actionId).isApplied?.({
                editingElement,
                param: actionParam,
                value: actionValue,
            });
            return comp.props.inverseAction ? !isApplied : isApplied;
        });
        // If there is no `isApplied` method for the widget return false
        if (areActionsActiveTabs.every((el) => el === undefined)) {
            return false;
        }
        // If `isApplied` is explicitly false for an action return false
        if (areActionsActiveTabs.some((el) => el === false)) {
            return false;
        }
        // `isApplied` is true for at least one action
        return true;
    }
    return {
        getAllActions: getAllActions,
        callOperation: callOperation,
        isApplied: isApplied,
    };
}
