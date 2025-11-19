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

// Selectors for special cases where snippet options are bound to parent
// containers instead of the snippet itself.
export const BLOCKQUOTE_PARENT_HANDLERS = ".s_reviews_wall .row > div";
export const BLOCKQUOTE_DISABLE_WIDTH_APPLY_TO = ":scope > .s_blockquote";
export const SPECIAL_BLOCKQUOTE_SELECTOR = `${BLOCKQUOTE_PARENT_HANDLERS} > .s_blockquote`;

/**
 * @typedef { import("../../../../html_editor/static/src/editor").EditorContext } EditorContext
 */

/**
 * Verifies that a DOM node is still attached to a live document.
 *
 * @param {Node | undefined} el - The node to check.
 * @returns {Boolean} - True when the node belongs to an active document.
 */
function isConnectedElement(el) {
    return el && el.isConnected && !!el.ownerDocument.defaultView;
}

/**
 * Builds a reactive state that refreshes whenever there is a DOM update.
 *
 * The provided `getState` callback runs during component start and after every
 * `DOM_UPDATED` event. The returned state object is updated in place only when
 * the current editing element is available and still connected to the document
 * (unless `checkEditingElement` is disabled).
 *
 * @param {Function} getState - The function that computes the component state.
 * @param {{checkEditingElement: Boolean}} - Whether to update the state of the
 * element if there is no editing element available.
 * @returns {Object} - A reactive object (the state) that will be updated at
 * each dom update.
 */
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

/**
 * Extracts action metadata (from the component props or context).
 *
 * @returns {{
 *   actionId: String | undefined,
 *   actionParam: String | undefined,
 *   actionValue: String | undefined,
 *   classAction: String | undefined,
 *   styleAction: String | undefined,
 *   styleActionValue: String | undefined,
 *   attributeAction: String | undefined,
 *   attributeActionValue: String | undefined
 * }}
 */
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

/**
 * Returns the result of a `querySelectorAll` applied on each elements of the
 * targets.
 * @param {Array<HTMLElement>} targets - The elements on which to apply the
 * `querySelectorAll`.
 * @param {String} selector - The css selector to use on the `querySelectorAll`.
 * @returns {Array<HTMLElement>} - Elements that are descendants of `targets`
 * and matches the selector.
 */
function querySelectorAll(targets, selector) {
    const elements = new Set();
    for (const target of targets) {
        for (const el of target.querySelectorAll(selector)) {
            elements.add(el);
        }
    }
    return [...elements];
}

/**
 * Handles the update of the editing elements of a builder component.
 */
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

/**
 * Registers a builder component in the dependency manager for cross-option
 * communication.
 *
 * The registration is optionally deferred until the `onReady` promise resolves,
 * ensuring `prepare` hooks complete before other components rely on the
 * provided item.
 *
 * @param {String} id - The builder component identifier.
 * @param {Object} item - Values and callbacks that other components can consume
 * via the manager.
 * @param {{onReady: Promise}} - Optional promise deferring the registration.
 */
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

/**
 * Produces an accessor that reports whether dependency-managed items are
 * active.
 *
 * @returns {Function} - A function to subscribe to each requested id.
 */
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

    const state = useItemStatus(listenedKeys, isActive);
    return function isActiveItem(itemId) {
        listenedKeys.add(itemId);
        if (state[itemId] === undefined) {
            return isActive(itemId);
        }
        return state[itemId];
    };
}

/**
 * Produces an accessor that reads the value of dependency-managed items.
 *
 * @returns {Function} - A function to subscribe to each requested id.
 */
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

    const state = useItemStatus(listenedKeys, getValue);
    return function getItemValue(itemId) {
        listenedKeys.add(itemId);
        if (!(itemId in state)) {
            return getValue(itemId);
        }
        return state[itemId];
    };
}

/**
 *
 * Tracks the currently selected option among selectable builder items.
 *
 * The hook collects selectable descriptors from descendants, resolves which one
 * is active based on their priority, and optionally registers the collection
 * under the provided dependency id.
 *
 * @param {String | undefined} id - If provided, the identifier used to expose
 * the selectable collection via dependencies.
 * @param {{onItemChange: Function}} - Optional callback executed at selected item
 * computation.
 */
export function useSelectableComponent(id, { onItemChange } = {}) {
    useBuilderComponent();
    const selectableItems = [];
    const refreshCurrentItemDebounced = useDebounced(refreshCurrentItem, 0, { immediate: true });
    const env = useEnv();

    const state = reactive({
        currentSelectedItem: null,
    });

    function refreshCurrentItem() {
        if (env.editor.isDestroyed) {
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

/**
 * Handles selectable item behavior so that it cooperates with selectable
 * component.
 *
 * The hook exposes the same operation helpers as
 * `useClickableBuilderComponent`, while registering the item inside the nearest
 * selectable context and keeping an `isActive` state synchronized with the
 * current selection.
 *
 * @param {String | undefined} id - Dependency identifier representing this
 * selectable item.
 * @param {{getLabel: Function}} - Function that returns the label of the
 * selectable item.
 * @returns {{state: Object, operation: Object}} - The state and the actions
 * to execute once the item is hovered/selected etc.
 */
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

/**
 * Schedules the "prepare" phase for every action related to the current
 * component.
 *
 * @param {Function} getAllActions - Function that returns all the actions
 * related to a builder component.
 * @returns {Promise | undefined} - A promise that is resolved as soon as the
 * "prepare" phase of all the actions related to a builder option is finished.
 */
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

/**
 * Collects reload metadata exposed by any of the component actions.
 *
 * @param {Function} getAllActions - Supplier returning all the actions related
 * to a builder component.
 * @returns {Object} - Wrapper containing the reload configuration, if
 * available.
 */
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

/**
 * Evaluates whether a builder component has a preview capability.
 *
 * @param {Function} getAllActions - Supplier returning all the actions related
 * to a builder component.
 * @returns {Boolean} - True when each action supports preview and the component
 * is configured to allow it.
 */
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

/**
 * Evaluates whether the actions request a loading indicator while committing.
 *
 * @param {Function} getAllActions - Supplier returning all the actions related
 * to a builder component.
 * @returns {Boolean} - True unless at least one action explicitly disables the
 * effect.
 */
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

/**
 * Sets up the full action lifecycle for a clickable builder component.
 *
 * The hook wires the component into the builder context, resolves all related
 * actions (including inherited ones), runs their `prepare` phases, and exposes
 * helpers to commit/preview/revert while integrating with history, reload,
 * and dependency tracking.
 * @returns {{
 * operation: Object,
 * isApplied: Function,
 * clean: Function,
 * priority: Number,
 * getActions: Function,
 * onReady: Promise | undefined,
 * }}
 */
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

    let preventNextPreview = false;
    const operation = {
        commit: () => {
            preventNextPreview = false;
            if (reload) {
                callOperation(operationWithReload);
            } else {
                callOperation(applyOperation.commit, {
                    operationParams: {
                        withLoadingEffect: withLoadingEffect,
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
                },
            });
        },
        revert: () => {
            preventNextPreview = false;
            // The `next` will cancel the previous operation, which will revert
            // the operation in case of a preview.
            comp.env.editor.shared.operation.next();
        },
    };

    if (!hasPreview) {
        operation.preview = () => {};
    }

    /**
     * Handles the `clean` operations related to the builder option.
     * @param {Array<Object>} nextApplySpecs - The action specifications that
     * triggered the clean.
     * @param {Boolean} isPreviewing - Whether the actions should be executed in
     * preview mode or not.
     * @returns {Promise} - A promise that is resolved when the `clean`
     * operations related to the builder option are finished.
     */
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

    /**
     * Handles the "clean" and "apply" of all the actions related to a builder
     * component.
     * @param {Array<Object>} applySpecs - An array where each element contains
     * an html element and the action to apply on it.
     * @param {Boolean} isPreviewing - Whether the actions should be in preview
     * mode or not.
     */
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

/**
 * Wraps an apply routine so the editor reloads after the actions run.
 *
 * @param {Function} callApply - Function executing the actions related to the
 * current builder component.
 * @param {Object} reload - Reload configuration extracted from actions.
 * @returns {Function}
 */
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

/**
 * Normalizes user input by falling back to the configured default when needed.
 *
 * @param {String} userInputValue - Raw value provided by the user.
 * @param {String | undefined} defaultValue - Default value declared on the
 * component.
 * @param {Function} formatRawValue - Formatter applied to the default before
 * returning it.
 * @returns {String} - The original input or the formatted default when the
 * input is empty.
 */
function getValueWithDefault(userInputValue, defaultValue, formatRawValue) {
    if (defaultValue !== undefined) {
        if (!userInputValue || (typeof userInputValue === "string" && !userInputValue.trim())) {
            return formatRawValue(defaultValue);
        }
    }
    return userInputValue;
}

/**
 * Configures an input-style builder component that reads, previews, and commits
 * values.
 *
 * The hook computes the current value from related actions, normalizes user
 * input with optional format/parse helpers, and exposes commit/preview logic
 * that cooperates with history, reload, and dependency tracking.
 *
 * @param {{
 * id: String | undefined,
 * defaultValue: String | undefined,
 * formatRawValue: Function | undefined,
 * parseDisplayValue: Function | undefined,
 * }}
 * @returns {{
 * state: Object,
 * commit: Function,
 * preview: Function,
 * onReady: Promise | undefined,
 * }}
 */
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
            callOperation(operationWithReload, { userInputValue: rawValue });
        } else {
            callOperation(applyOperation.commit, {
                userInputValue: rawValue,
                withLoadingEffect: withLoadingEffect,
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

/**
 * Generates a helper that toggles the visibility of an element referenced by
 * name.
 *
 * @param {String} refName - Name of the Owl reference pointing to the container
 * to toggle.
 * @returns {Function} - Callback that hides the element when content is absent.
 */
export function useApplyVisibility(refName) {
    const ref = useRef(refName);
    return (hasContent) => {
        ref.el?.classList.toggle("d-none", !hasContent);
    };
}

/**
 * Observes a content slot and informs a callback when visible nodes are
 * present.
 *
 * @param {String} contentName - Name of the Owl reference containing the
 * observed content.
 * @param {Function} callback - Called whenever visibility should change.
 */
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

/**
 * Returns a debounced commit handler tied to an input builder component.
 *
 * @param {import("@web/core/utils/hooks").Ref} ref - Reference to the input
 * element whose value should be committed.
 * @returns {Function} Debounced callback that normalizes and commits the input
 * value.
 */
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

/**
 * Aggregates all actions linked to a builder component and exposes execution
 * helpers.
 *
 * The helpers resolve shorthand, custom, and inherited actions, orchestrate
 * their application through the history mutex, and report whether the option is
 * currently applied.
 *
 * @param {typeof import("@odoo/owl").Component} comp - The builder component
 * requesting the actions.
 * @returns {{getAllActions: Function,
 * callOperation: Function,
 * isApplied: Function}}
 * Helper functions related to the component.
 */
export function getAllActionsAndOperations(comp) {
    const inheritedActionIds =
        comp.props.inheritedActions || comp.env.weContext.inheritedActions || [];

    /**
     * Computes the action specifications related to a builder component. An
     * action specification contains a target editing element and all the action
     * information.
     * @param {Array<Object>} actions - The actions related to a builder
     * components.
     * @param {String | undefined} userInputValue - If defined, the input value
     * provided by the user.
     * @returns {Array<Object>}
     */
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
    /**
     * Returns the list of shorthand actions related to a builder component (the
     * one defined in its props and in its context).
     * @returns {Array<Object>}
     */
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
    /**
     * Returns the custom action related to a builder component if any.
     * @returns {Object|undefined}
     */
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
    /**
     * Returns all the actions (shorthand, custom and inherited) related to a
     * builder component.
     * @returns {Array<Object>}
     */
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
    /**
     * Handles the `load` phase of actions and put the actions in a mutex in
     * order to be executed.
     * @param {Function} fn - A function to add in the mutex
     * @param {Object} params - Parameters that describe if the function can be
     * cancellable, how it should be cancellable, etc...
     */
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
    /**
     * Evaluates if an option is considered applied.
     * @returns {Boolean | undefined}
     */
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
        // If there is no `isApplied` method related to the builder component
        // return false.
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

/**
 * Determines whether an action should run its "clean" phase instead of "apply".
 *
 * @param {import("@odoo/owl").Component} comp - The builder component requesting the action execution.
 * @param {Boolean} hasClean - Whether the action exposes a `clean` handler.
 * @param {Boolean} isApplied - Current applied status of the action.
 * @returns {Boolean} - Whether the "clean" phase should be executed rather than
 * the "apply".
 */
function _shouldClean(comp, hasClean, isApplied) {
    if (!hasClean) {
        return false;
    }
    const shouldToggle = !comp.env.selectableContext;
    const shouldClean = shouldToggle && isApplied;
    return comp.props.inverseAction ? !shouldClean : shouldClean;
}

/**
 * Ensures action parameters are shaped as plain objects consumable by actions.
 *
 * @param {any} param - Parameter provided by props or the builder context.
 * @returns {Object} - Original object or a `{mainParam: param}` wrapper.
 */
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

/**
 * Base class shared by builder option components to preload dependencies and
 * helpers.
 *
 * It injects the `isActiveItems` accessor and merges the shared builder
 * components into the extending component's catalog.
 */
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

/**
 * Creates a reactive state object that tracks and updates the status of
 * specific builder components whenever dependencies in the environment change
 * or at each DOM update.
 *
 * @param {Set<String>} listenedKeys - A set of builder components to track.
 * @param {Function} newStateFn - The function to update the state of listened
 * builder components.
 * @returns {Object} - A reactive object.
 */
function useItemStatus(listenedKeys, newStateFn) {
    const env = useEnv();
    const getState = () => {
        const newState = {};
        for (const itemId of listenedKeys) {
            newState[itemId] = newStateFn(itemId);
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
    return state;
}
