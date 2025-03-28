import { isTextNode } from "@html_editor/utils/dom_info";
import {
    Component,
    onMounted,
    onWillDestroy,
    onWillStart,
    onWillUpdateProps,
    useComponent,
    useEffect,
    useEnv,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export function useDomState(getState, { checkEditingElement = true, onReady } = {}) {
    const env = useEnv();
    const isValid = (el) => (!el && !checkEditingElement) || (el && el.isConnected);
    const handler = () => {
        const editingElement = env.getEditingElement();
        if (isValid(editingElement)) {
            Object.assign(state, getState(editingElement));
        }
    };
    const state = useState({});
    if (onReady) {
        onReady.then(() => {
            handler();
        });
    } else {
        handler();
    }

    useBus(env.editorBus, "DOM_UPDATED", handler);
    // Promise.resolve().then(() => env.editorBus.addEventListener("DOM_UPDATED", handler));
    // onWillDestroy(() => env.editorBus.removeEventListener("DOM_UPDATED", handler));
    return state;
}

export function useActionInfo() {
    const comp = useComponent();

    const getParam = (paramName) => {
        let param = comp.props[paramName];
        param = param === undefined ? comp.env.weContext[paramName] : param;
        if (typeof param === "object") {
            param = JSON.stringify(param);
        }
        return param;
    };

    const actionParam = getParam("actionParam");

    return {
        actionId: comp.props.action || comp.env.weContext.action,
        actionParam,
        actionValue: comp.props.actionValue,
        classAction: getParam("classAction"),
        styleAction: getParam("styleAction"),
        styleActionValue: comp.props.styleActionValue,
        attributeAction: getParam("attributeAction"),
        attributeActionValue: comp.props.attributeActionValue,
    };
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
    let editingElements;
    let applyTo = comp.props.applyTo;
    const updateEditingElements = () => {
        editingElements = applyTo
            ? querySelectorAll(oldEnv.getEditingElements(), applyTo)
            : oldEnv.getEditingElements();
    };
    updateEditingElements();
    oldEnv.editorBus.addEventListener("UPDATE_EDITING_ELEMENT", updateEditingElements);
    onWillUpdateProps((nextProps) => {
        if (comp.props.applyTo !== nextProps.applyTo) {
            applyTo = nextProps.applyTo;
            oldEnv.editorBus.trigger("UPDATE_EDITING_ELEMENT");
            oldEnv.editorBus.trigger("DOM_UPDATED");
        }
    });
    onWillDestroy(() => {
        oldEnv.editorBus.removeEventListener("UPDATE_EDITING_ELEMENT", updateEditingElements);
    });
    newEnv.getEditingElements = () => editingElements;
    newEnv.getEditingElement = () => editingElements[0];
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
export function useDependencyDefinition(id, item, { onReady } = {}) {
    const comp = useComponent();
    if (onReady) {
        onReady.then(() => {
            comp.env.dependencyManager.add(id, item);
        });
    } else {
        comp.env.dependencyManager.add(id, item);
    }

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

function useIsActiveItem() {
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
    useBus(env.editorBus, "DOM_UPDATED", refreshCurrentItem);
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
            items: selectableItems,
        },
    });
}
export function useSelectableItemComponent(id, { getLabel = () => {} } = {}) {
    const { operation, isApplied, getActions, priority, clean, onReady } =
        useClickableBuilderComponent();
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
        onWillStart(async () => {
            await Promise.resolve();
            state.isActive = isSelectableActive();
        });
    }

    if (id) {
        useDependencyDefinition(
            id,
            {
                isActive: isSelectableActive,
                getActions,
                cleanSelectedItem: env.selectableContext?.cleanSelectedItem,
            },
            { onReady }
        );
    }

    const state = useDomState(
        () => ({
            isActive: isSelectableActive(),
        }),
        { onReady }
    );

    return { state, operation };
}
export function useClickableBuilderComponent() {
    useBuilderComponent();
    const comp = useComponent();
    const { getAllActions, callOperation, isApplied } = getAllActionsAndOperations(comp);
    const getAction = comp.env.editor.shared.builderActions.getAction;
    const asyncActions = [];
    let hasReloadAction = false;
    let getReloadUrl;
    for (const descr of getAllActions()) {
        if (descr.actionId) {
            const action = getAction(descr.actionId);
            if (action.prepare) {
                asyncActions.push({ action, descr });
            }
            if (action.isReload) {
                hasReloadAction = true;
                getReloadUrl = action.getReloadUrl;
            }
        }
    }
    let onReady;
    if (asyncActions.length) {
        let resolve;
        onReady = new Promise((r) => {
            resolve = r;
        });
        onWillStart(async function () {
            await Promise.all(asyncActions.map((obj) => obj.action.prepare(obj.descr)));
            resolve();
        });
    }

    const applyOperation = comp.env.editor.shared.history.makePreviewableOperation(callApply);
    const inheritedActionIds =
        comp.props.inheritedActions || comp.env.weContext.inheritedActions || [];

    const hasPreview =
        !hasReloadAction &&
        (comp.props.preview === true ||
            (comp.props.preview === undefined && comp.env.weContext.preview !== false));

    const getReloadTarget = (el) => {
        if (el.closest("header")) {
            return "header";
        }
        if (el.closest("main")) {
            return "main";
        }
        if (el.closest("footer")) {
            return "footer";
        }
        return null;
    };

    const operation = {
        commit: () => {
            if (hasReloadAction) {
                callOperation(async (...args) => {
                    const { editingElement } = args[0][0];
                    await Promise.all([
                        callApply(...args),
                        comp.env.editor.shared.savePlugin.save(),
                    ]);
                    const target = getReloadTarget(editingElement);
                    const url = getReloadUrl?.();
                    comp.env.editor.config.reloadEditor({ target, url });
                });
            } else {
                callOperation(applyOperation.commit);
            }
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
                    selectableContext: comp.env.selectableContext,
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

    async function callApply(applySpecs) {
        comp.env.selectableContext?.cleanSelectedItem(applySpecs);
        const cleans = inheritedActionIds
            .map((actionId) => comp.env.dependencyManager.get(actionId).cleanSelectedItem)
            .filter(Boolean);
        for (const clean of new Set(cleans)) {
            clean(applySpecs);
        }
        const hasClean = applySpecs.some((applySpec) => applySpec.clean);
        const shouldClean = _shouldClean(comp, hasClean, isApplied());
        const proms = [];
        for (const applySpec of applySpecs) {
            if (shouldClean) {
                proms.push(
                    applySpec.clean?.({
                        editingElement: applySpec.editingElement,
                        param: applySpec.actionParam,
                        value: applySpec.actionValue,
                        dependencyManager: comp.env.dependencyManager,
                        selectableContext: comp.env.selectableContext,
                    })
                );
            } else {
                proms.push(
                    applySpec.apply({
                        editingElement: applySpec.editingElement,
                        param: applySpec.actionParam,
                        value: applySpec.actionValue,
                        loadResult: applySpec.loadResult,
                        dependencyManager: comp.env.dependencyManager,
                        selectableContext: comp.env.selectableContext,
                    })
                );
            }
        }
        await Promise.all(proms);
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
        onReady,
    };
}
export function useInputBuilderComponent({
    id,
    defaultValue,
    formatRawValue = (rawValue) => rawValue,
    parseDisplayValue = (displayValue) => displayValue,
} = {}) {
    const comp = useComponent();
    const { getAllActions, callOperation } = getAllActionsAndOperations(comp);
    const getAction = comp.env.editor.shared.builderActions.getAction;
    const state = useDomState(getState);
    const applyOperation = comp.env.editor.shared.history.makePreviewableOperation((applySpecs) => {
        for (const applySpec of applySpecs) {
            applySpec.apply({
                editingElement: applySpec.editingElement,
                param: applySpec.actionParam,
                value: applySpec.actionValue,
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
        const actionValue = getAction(actionId).getValue({ editingElement, param: actionParam });
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
        comp.env.editor.shared.operation.next(() => fn(actionsSpecs), {
            load: async () => {
                const hasClean = actionsSpecs.some((applySpec) => applySpec.clean);
                return Promise.all(
                    actionsSpecs.map(async (applySpec) => {
                        if (!applySpec.load) {
                            return;
                        }
                        if (_shouldClean(comp, hasClean, isApplied())) {
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
                );
            },
            ...params.operationParams,
        });
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
function _shouldClean(comp, hasClean, isApplied) {
    if (!hasClean) {
        return false;
    }
    const shouldToggle = !comp.env.selectableContext;
    const shouldClean = shouldToggle && isApplied;
    return comp.props.inverseAction ? !shouldClean : shouldClean;
}

export class BaseOptionComponent extends Component {
    static components = {};

    setup() {
        this.isActiveItem = useIsActiveItem();
        const comp = useComponent();
        const editor = comp.env.editor;
        if (!comp.constructor.components) {
            comp.constructor.components = {};
        }
        const Components = editor.shared.builderComponents.getComponents();
        Object.assign(comp.constructor.components, Components);
    }
}
