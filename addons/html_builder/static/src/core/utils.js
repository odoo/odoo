import { isElement, isTextNode } from "@html_editor/utils/dom_info";
import {
    Component,
    onMounted,
    onWillDestroy,
    onWillStart,
    onWillUpdateProps,
    reactive,
    toRaw,
    useComponent,
    useEffect,
    useEnv,
    useRef,
    useState,
    useSubEnv,
} from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { effect } from "@web/core/utils/reactive";
import { useDebounced } from "@web/core/utils/timing";

/**
 * @typedef { import("../../../../html_editor/static/src/editor").EditorContext } EditorContext
 */

function isConnectedElement(el) {
    return el && el.isConnected && !!el.ownerDocument.defaultView;
}

export function useDomState(getState, { checkEditingElement = true } = {}) {
    const env = useEnv();
    const isValid = (el) => (!el && !checkEditingElement) || isConnectedElement(el);
    const handler = async (ev) => {
        const editingElement = env.getEditingElement();
        if (isValid(editingElement)) {
            const newStatePromise = getState(editingElement);
            if (ev) {
                ev.detail.getStatePromises.push(newStatePromise);
                const newState = await newStatePromise;
                const shouldApply = await ev.detail.updatePromise;
                if (shouldApply) {
                    Object.assign(state, newState);
                }
            } else {
                Object.assign(state, await newStatePromise);
            }
        }
    };
    const state = useState({});
    onWillStart(handler);
    useBus(env.editorBus, "DOM_UPDATED", handler);
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
    onWillUpdateProps(async (nextProps) => {
        if (comp.props.applyTo !== nextProps.applyTo) {
            applyTo = nextProps.applyTo;
            oldEnv.editorBus.trigger("UPDATE_EDITING_ELEMENT");
            await oldEnv.triggerDomUpdated();
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
    const ignore = comp.env.ignoreBuilderItem;
    if (onReady) {
        onReady.then(() => {
            comp.env.dependencyManager.add(id, item, ignore);
        });
    } else {
        comp.env.dependencyManager.add(id, item, ignore);
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
        if (!(itemId in state)) {
            return getValue(itemId);
        }
        return state[itemId];
    };
}

export function useSelectableComponent(id, { onItemChange } = {}) {
    useBuilderComponent();
    const selectableItems = [];
    const refreshCurrentItemDebounced = useDebounced(refreshCurrentItem, 0, { immediate: true });
    const env = useEnv();

    const state = reactive({
        currentSelectedItem: null,
    });

    function refreshCurrentItem() {
        if (env.editor.isDestroyed || env.editor.shared.history.getIsPreviewing()) {
            return;
        }
        let currentItem;
        let itemPriority = 0;
        for (const selectableItem of selectableItems) {
            if (selectableItem.isApplied() && selectableItem.priority >= itemPriority) {
                currentItem = selectableItem;
                itemPriority = selectableItem.priority;
            }
        }
        if (currentItem && currentItem !== toRaw(state.currentSelectedItem)) {
            state.currentSelectedItem = currentItem;
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
        if (state.currentSelectedItem) {
            return state.currentSelectedItem.clean(...args);
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
            items: selectableItems,
            refreshCurrentItem: () => refreshCurrentItem(),
            getSelectableState: () => state,
        },
    });
}

export function useSelectableItemComponent(id, { getLabel = () => {} } = {}) {
    const { operation, isApplied, getActions, priority, clean, onReady } =
        useClickableBuilderComponent();
    const env = useEnv();

    let isSelectableActive = isApplied;
    let state;
    if (env.selectableContext) {
        const selectableState = env.selectableContext.getSelectableState();
        isSelectableActive = () => {
            env.selectableContext.refreshCurrentItem();
            return (
                toRaw(selectableState.currentSelectedItem) === selectableItem ||
                (id && selectableState.currentSelectedItem?.id === id)
            );
        };

        const selectableItem = {
            isApplied,
            priority,
            getLabel,
            clean,
            getActions,
            id,
        };

        env.selectableContext.addSelectableItem(selectableItem);
        state = useState({
            isActive: false,
        });
        effect(
            ({ currentSelectedItem }) => {
                state.isActive =
                    toRaw(currentSelectedItem) === selectableItem ||
                    (id && currentSelectedItem?.id === id);
            },
            [selectableState]
        );
        env.selectableContext.refreshCurrentItem();
        onMounted(env.selectableContext.update);
        onWillDestroy(() => {
            env.selectableContext.removeSelectableItem(selectableItem);
        });
    } else {
        state = useDomState(async () => {
            await onReady;
            return {
                isActive: isSelectableActive(),
            };
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

    return { state, operation };
}

function usePrepareAction(getAllActions) {
    const env = useEnv();
    const getAction = env.editor.shared.builderActions.getAction;
    const asyncActions = [];
    for (const descr of getAllActions()) {
        if (descr.actionId) {
            const action = getAction(descr.actionId);
            if (action.has("prepare")) {
                asyncActions.push({ action, descr });
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
        onWillUpdateProps(async ({ actionParam, actionValue }) => {
            onReady = new Promise((r) => {
                resolve = r;
            });
            // TODO: should we support updating actionId?
            await Promise.all(
                asyncActions.map((obj) =>
                    obj.action.prepare({
                        ...obj.descr,
                        actionParam: convertParamToObject(actionParam),
                        actionValue,
                    })
                )
            );
            resolve();
        });
    }
    return onReady;
}

function useReloadAction(getAllActions) {
    const env = useEnv();
    const getAction = env.editor.shared.builderActions.getAction;
    let reload = false;
    for (const descr of getAllActions()) {
        if (descr.actionId) {
            const action = getAction(descr.actionId);
            if (action.reload) {
                reload = action.reload;
            }
        }
    }
    return { reload };
}

export function useHasPreview(getAllActions) {
    const comp = useComponent();
    const getAction = comp.env.editor.shared.builderActions.getAction;

    let hasPreview = true;
    for (const descr of getAllActions()) {
        if (descr.actionId) {
            const action = getAction(descr.actionId);
            if (action.preview === false) {
                hasPreview = false;
            }
        }
    }

    return (
        hasPreview &&
        (comp.props.preview === true ||
            (comp.props.preview === undefined && comp.env.weContext.preview !== false))
    );
}

function useWithLoadingEffect(getAllActions) {
    const env = useEnv();
    const getAction = env.editor.shared.builderActions.getAction;
    let withLoadingEffect = true;
    for (const descr of getAllActions()) {
        if (descr.actionId) {
            const action = getAction(descr.actionId);
            if (action.withLoadingEffect === false) {
                withLoadingEffect = false;
            }
        }
    }

    return withLoadingEffect;
}

function useCanTimeout(getAllActions) {
    const env = useEnv();
    const getAction = env.editor.shared.builderActions.getAction;
    let canTimeout = true;
    for (const descr of getAllActions()) {
        if (descr.actionId) {
            const action = getAction(descr.actionId);
            if (action.canTimeout === false) {
                canTimeout = false;
            }
        }
    }

    return canTimeout;
}

export function revertPreview(editor) {
    if (editor.isDestroyed) {
        return;
    }
    // The `next` will cancel the previous operation, which will revert
    // the operation in case of a preview.
    return editor.shared.operation.next();
}

export function useClickableBuilderComponent() {
    useBuilderComponent();
    const comp = useComponent();
    const { getAllActions, callOperation, isApplied } = getAllActionsAndOperations(comp);
    const getAction = comp.env.editor.shared.builderActions.getAction;

    const onReady = usePrepareAction(getAllActions);
    const { reload } = useReloadAction(getAllActions);

    const applyOperation = comp.env.editor.shared.history.makePreviewableAsyncOperation(callApply);
    const inheritedActionIds =
        comp.props.inheritedActions || comp.env.weContext.inheritedActions || [];

    const hasPreview = useHasPreview(getAllActions);
    const operationWithReload = useOperationWithReload(callApply, reload);

    const withLoadingEffect = useWithLoadingEffect(getAllActions);
    const canTimeout = useCanTimeout(getAllActions);

    let preventNextPreview = false;
    const operation = {
        commit: () => {
            preventNextPreview = false;
            if (reload) {
                callOperation(operationWithReload, {
                    operationParams: {
                        withLoadingEffect: withLoadingEffect,
                        canTimeout: canTimeout,
                    },
                });
            } else {
                callOperation(applyOperation.commit, {
                    operationParams: {
                        withLoadingEffect: withLoadingEffect,
                        canTimeout: canTimeout,
                    },
                });
            }
        },
        preview: () => {
            // Avoid previewing the same option twice.
            if (preventNextPreview) {
                return;
            }
            preventNextPreview = true;
            callOperation(applyOperation.preview, {
                preview: true,
                operationParams: {
                    cancellable: true,
                    cancelPrevious: () => applyOperation.revert(),
                    canTimeout: canTimeout,
                },
            });
        },
        revert: () => {
            preventNextPreview = false;
            revertPreview(comp.env.editor);
        },
    };

    if (!hasPreview) {
        operation.preview = () => {};
    }

    function clean(nextApplySpecs, isPreviewing) {
        const proms = [];
        for (const { actionId, actionParam, actionValue } of getAllActions()) {
            for (const editingElement of comp.env.getEditingElements()) {
                let nextAction;
                proms.push(
                    getAction(actionId).clean?.({
                        isPreviewing,
                        editingElement,
                        params: actionParam,
                        value: actionValue,
                        dependencyManager: comp.env.dependencyManager,
                        selectableContext: comp.env.selectableContext,
                        get nextAction() {
                            nextAction =
                                nextAction ||
                                nextApplySpecs.find((a) => a.actionId === actionId) ||
                                {};
                            return {
                                params: nextAction.actionParam,
                                value: nextAction.actionValue,
                            };
                        },
                    })
                );
            }
        }
        return Promise.all(proms);
    }

    async function callApply(applySpecs, isPreviewing) {
        await comp.env.selectableContext?.cleanSelectedItem(applySpecs, isPreviewing);
        const cleans = inheritedActionIds
            .map((actionId) => comp.env.dependencyManager.get(actionId).cleanSelectedItem)
            .filter(Boolean);
        const cleanPromises = [];
        for (const clean of new Set(cleans)) {
            cleanPromises.push(clean(applySpecs, isPreviewing));
        }
        await Promise.all(cleanPromises);
        const cleanOrApplyProms = [];
        const isAlreadyApplied = isApplied();
        for (const applySpec of applySpecs) {
            const hasClean = !!applySpec.clean;
            const shouldClean = _shouldClean(comp, hasClean, isAlreadyApplied);
            if (shouldClean) {
                cleanOrApplyProms.push(
                    applySpec.action.clean({
                        isPreviewing,
                        editingElement: applySpec.editingElement,
                        params: applySpec.actionParam,
                        value: applySpec.actionValue,
                        loadResult: applySpec.loadOnClean ? applySpec.loadResult : null,
                        dependencyManager: comp.env.dependencyManager,
                        selectableContext: comp.env.selectableContext,
                    })
                );
            } else {
                cleanOrApplyProms.push(
                    applySpec.action.apply({
                        isPreviewing,
                        editingElement: applySpec.editingElement,
                        params: applySpec.actionParam,
                        value: applySpec.actionValue,
                        loadResult: applySpec.loadResult,
                        dependencyManager: comp.env.dependencyManager,
                        selectableContext: comp.env.selectableContext,
                    })
                );
            }
        }
        await Promise.all(cleanOrApplyProms);
    }
    function getPriority() {
        return (
            getAllActions()
                .map(
                    (a) =>
                        getAction(a.actionId).getPriority?.({
                            params: a.actionParam,
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
function useOperationWithReload(callApply, reload) {
    const env = useEnv();
    return async (...args) => {
        const { editingElement } = args[0][0];
        await callApply(...args);
        env.editor.shared.history.addStep();
        await env.editor.shared.savePlugin.save();
        const target = env.editor.shared.builderOptions.getReloadSelector(editingElement);
        const url = reload.getReloadUrl?.();
        await env.editor.config.reloadEditor({ target, url });
    };
}

function getValueWithDefault(userInputValue, defaultValue, formatRawValue) {
    if (defaultValue !== undefined) {
        if (!userInputValue || (typeof userInputValue === "string" && !userInputValue.trim())) {
            return formatRawValue(defaultValue);
        }
    }
    return userInputValue;
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

    const onReady = usePrepareAction(getAllActions);
    const { reload } = useReloadAction(getAllActions);

    const withLoadingEffect = useWithLoadingEffect(getAllActions);
    const canTimeout = useCanTimeout(getAllActions);

    onWillUpdateProps((nextProps) => {
        if ("default" in nextProps) {
            defaultValue = nextProps.default;
        }
    });

    async function callApply(applySpecs, isPreviewing) {
        const proms = [];
        for (const applySpec of applySpecs) {
            proms.push(
                applySpec.action.apply({
                    isPreviewing,
                    editingElement: applySpec.editingElement,
                    params: applySpec.actionParam,
                    value: applySpec.actionValue,
                    loadResult: applySpec.loadResult,
                    dependencyManager: comp.env.dependencyManager,
                })
            );
        }
        await Promise.all(proms);
    }

    const applyOperation = comp.env.editor.shared.history.makePreviewableAsyncOperation(callApply);
    const operationWithReload = useOperationWithReload(callApply, reload);
    function getState(editingElement) {
        if (!isConnectedElement(editingElement)) {
            // TODO try to remove it. We need to move hook in BuilderComponent
            return {};
        }
        const actionWithGetValue = getAllActions().find(
            ({ actionId }) => getAction(actionId).getValue
        );
        const { actionId, actionParam } = actionWithGetValue;
        const actionValue =
            getAction(actionId).getValue({ editingElement, params: actionParam }) || defaultValue;
        return {
            value: actionValue,
        };
    }

    function commit(userInputValue) {
        userInputValue = getValueWithDefault(userInputValue, defaultValue, formatRawValue);
        const rawValue = parseDisplayValue(userInputValue);
        if (reload) {
            callOperation(operationWithReload, {
                userInputValue: rawValue,
                operationParams: {
                    withLoadingEffect: withLoadingEffect,
                    canTimeout: canTimeout,
                },
            });
        } else {
            callOperation(applyOperation.commit, {
                userInputValue: rawValue,
                operationParams: {
                    withLoadingEffect: withLoadingEffect,
                    canTimeout: canTimeout,
                },
            });
        }
        if (rawValue === null || (rawValue === defaultValue && rawValue === state.value)) {
            state.value = rawValue;
        }
        // If the parsed value is not equivalent to the user input, we want to
        // normalize the displayed value. It is useful in cases of invalid
        // input and allows to fall back to the output of parseDisplayValue.
        return rawValue !== undefined ? formatRawValue(rawValue) : "";
    }

    const shouldPreview = useHasPreview(getAllActions);
    function preview(userInputValue) {
        if (shouldPreview) {
            userInputValue = getValueWithDefault(userInputValue, defaultValue, formatRawValue);
            callOperation(applyOperation.preview, {
                preview: true,
                userInputValue: parseDisplayValue(userInputValue),
                operationParams: {
                    cancellable: true,
                    cancelPrevious: () => applyOperation.revert(),
                    canTimeout: canTimeout,
                },
            });
        }
    }

    if (id) {
        useDependencyDefinition(
            id,
            {
                type: "input",
                getValue: () => state.value,
            },
            { onReady }
        );
    }

    return {
        state,
        commit,
        preview,
        onReady,
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
        const hasContent = [...contentRef.el.childNodes].some(
            (el) =>
                (isTextNode(el) && el.textContent !== "") ||
                (isElement(el) && !el.classList.contains("d-none"))
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

export function useInputDebouncedCommit(ref) {
    const comp = useComponent();
    return useDebounced(() => {
        const normalizedDisplayValue = comp.commit(ref.el.value);
        ref.el.value = normalizedDisplayValue;
    }, 550);
    // ↑ 500 is the delay when holding keydown between the 1st and 2nd event
    // fired. Some additional delay by the browser may add another ~5-10ms.
    // We debounce above that threshold to keep a single history step when
    // holding up/down on a number or range input.
}

export const basicContainerBuilderComponentProps = {
    id: { type: String, optional: true },
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
        const overridableMethods = ["apply", "clean", "load", "loadOnClean"];
        const specs = [];
        for (let { actionId, actionParam, actionValue } of actions) {
            const action = getAction(actionId);
            // Take the action value defined by the clickable or the input given
            // by the user.
            actionValue = actionValue === undefined ? userInputValue : actionValue;
            for (const editingElement of comp.env.getEditingElements()) {
                const spec = {
                    editingElement,
                    actionId,
                    actionParam,
                    actionValue,
                    action,
                };
                // TODO Since the action is now in the spec, this shouldn't be
                // necessary anymore.
                for (const method of overridableMethods) {
                    if (!action.has || action.has(method)) {
                        spec[method] = action[method];
                    }
                }
                specs.push(spec);
            }
        }
        return specs;
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
        const isPreviewing = !!params.preview;
        const actionsSpecs = getActionsSpecs(getAllActions(), params.userInputValue);

        comp.env.editor.shared.operation.next(() => fn(actionsSpecs, isPreviewing), {
            load: async () =>
                Promise.all(
                    actionsSpecs.map(async (applySpec) => {
                        if (!applySpec.action.has("load")) {
                            return;
                        }
                        const hasClean = !!applySpec.action.has("clean");
                        if (!applySpec.loadOnClean && _shouldClean(comp, hasClean, isApplied())) {
                            // The element will be cleaned, do not load
                            return;
                        }
                        const result = await applySpec.action.load({
                            editingElement: applySpec.editingElement,
                            params: applySpec.actionParam,
                            value: applySpec.actionValue,
                        });
                        applySpec.loadResult = result;
                    })
                ),
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
            if (!isConnectedElement(editingElement)) {
                return false;
            }
            const isApplied = getAction(actionId).isApplied?.({
                editingElement,
                params: actionParam,
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
export function convertParamToObject(param) {
    if (param === undefined) {
        param = {};
    } else if (param instanceof Array || param instanceof Function || !(param instanceof Object)) {
        param = {
            ["mainParam"]: param,
        };
    }
    return param;
}

export class BaseOptionComponent extends Component {
    static components = {};
    static props = {};
    static template = "";

    setup() {
        /** @type {EditorContext} */
        const context = this.env.editor.shared.builderOptions.getBuilderOptionContext(
            this.constructor
        );
        /** @type { EditorContext['document'] } **/
        this.document = context.document;
        this.window = context.document.defaultView;
        /** @type { EditorContext['editable'] } **/
        this.editable = context.editable;
        /** @type { EditorContext['config'] } **/
        this.config = context.config;
        /** @type { EditorContext['services'] } **/
        this.services = context.services;
        /** @type { EditorContext['dependencies'] } **/
        this.dependencies = context.dependencies;
        /** @type { EditorContext['getResource'] } **/
        this.getResource = context.getResource;
        /** @type { EditorContext['dispatchTo'] } **/
        this.dispatchTo = context.dispatchTo;
        /** @type { EditorContext['delegateTo'] } **/
        this.delegateTo = context.delegateTo;

        this.isActiveItem = useIsActiveItem();
        const comp = useComponent();
        const editor = comp.env.editor;

        if (!comp.constructor.components) {
            comp.constructor.components = {};
        }
        const Components = editor.shared.builderComponents.getComponents();
        Object.assign(comp.constructor.components, Components);
    }
    /**
     * Check if the given items are active.
     *
     * Map over all items to listen for any reactive value changes.
     *
     * @param {string[]} itemIds - The IDs of the items to check.
     * @returns {boolean} - True if the item is active, false otherwise.
     */
    isActiveItems(itemIds) {
        return itemIds.map((i) => this.isActiveItem(i)).find(Boolean) || false;
    }
}
