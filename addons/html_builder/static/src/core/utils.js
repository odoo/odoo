import {
    reactive,
    useComponent,
    useEnv,
    useLayoutEffect,
    useRef,
    useState,
    useSubEnv,
} from "@web/owl2/utils";
import { isElement, isTextNode } from "@html_editor/utils/dom_info";
import { onMounted, onWillDestroy, onWillStart, onWillUpdateProps, status, toRaw } from "@odoo/owl";
import { convertNumericToUnit, getHtmlStyle } from "@html_editor/utils/formatting";
import { localization } from "@web/core/l10n/localization";
import { useBus } from "@web/core/utils/hooks";
import { effect } from "@web/core/utils/reactive";
import { useDebounced } from "@web/core/utils/timing";
import { BuilderAction } from "./builder_action";

// Selectors for special cases where snippet options are bound to parent
// containers instead of the snippet itself.
export const BLOCKQUOTE_PARENT_HANDLERS = ".s_reviews_wall .row > div";
export const CARD_PARENT_HANDLERS =
    ".s_three_columns .row > div, .s_comparisons .row > div, .s_cards_grid .row > div, .s_cards_soft .row > div, .s_product_list .row > div, .s_newsletter_centered .row > div, .s_company_team_spotlight .row > div, .s_comparisons_horizontal .row > div, .s_company_team_grid .row > div, .s_company_team_card .row > div, .s_carousel_cards_item";

/**
 * @typedef {((reload_context: Object, editingElement: HTMLElement) => reload_context)[]} reload_context_processors
 * @typedef { import("../../../../html_editor/static/src/editor").EditorContext } EditorContext
 */

function isConnectedElement(el) {
    return el && el.isConnected && !!el.ownerDocument.defaultView;
}

export function useDomState(getState, { checkEditingElement = true } = {}) {
    const component = useComponent();
    const env = useEnv();
    const isValid = (el) => (!el && !checkEditingElement) || isConnectedElement(el);
    const handler = async (ev) => {
        const editingElement = env.getEditingElement();
        if (isValid(editingElement)) {
            try {
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
            } catch (e) {
                if (!isValid(editingElement) || status(component) === "destroyed") {
                    return;
                }
                throw e;
            }
        }
    };
    const state = useState({});
    onWillStart(handler);
    useBus(env.editorBus, "DOM_UPDATED", handler);
    return state;
}

export function useActionInfo({ stringify = true } = {}) {
    const comp = useComponent();

    const getParam = (paramName) => {
        let param = comp.props[paramName];
        param = param === undefined ? comp.env.weContext[paramName] : param;
        if (stringify && typeof param === "object") {
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
        dataAttributeAction: getParam("dataAttributeAction"),
        dataAttributeActionValue: comp.props.dataAttributeActionValue,
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
    if (!oldEnv.langDir) {
        newEnv.langDir = {
            content: oldEnv.editor.config.isEditableRTL ? "rtl" : "ltr",
            builder: localization.direction,
        };
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
    const ltrRtlMappedItems = new Map();
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

    onMounted(() => {
        for (const [ltrRtlMapping, mappedItems] of ltrRtlMappedItems.entries()) {
            if (mappedItems.length === 1) {
                throw new Error(
                    `ltrRtlMapping "${ltrRtlMapping}" has been found only once. They should always come in pair and shouldn't have different render conditions.`
                );
            }
        }
    });

    function handleLtrRtl({ ltrRtlMapping, isLabelLinkedToContent, langDir }) {
        const mappedItems = ltrRtlMappedItems.get(ltrRtlMapping);
        if (mappedItems.length === 2) {
            const labelProps = ["title", "label", "slots"];
            if (langDir.content === "ltr" && langDir.builder === "ltr") {
                return;
            }
            if (langDir.builder === "rtl" && !isLabelLinkedToContent) {
                revertItemPropsState(mappedItems, labelProps);
            }
            // The action depends on whether both builder and iframe have the
            // same direction or not: if both are the same, the 1st button
            // should have a "start" action (in English: left = start, in
            // Arabic: right = start). If both are different, the 1st button
            // should have an "end" action (builder in English with an iframe
            // in Arabic: left = end, right = start).
            if (langDir.content !== langDir.builder) {
                const revertProps = [
                    "className",
                    "actionParam",
                    "actionValue",
                    "classAction",
                    "styleAction",
                    "styleActionValue",
                    "attributeAction",
                    "attributeActionValue",
                    "dataAttributeAction",
                    "dataAttributeActionValue",
                ];
                if (isLabelLinkedToContent) {
                    revertProps.push(...labelProps);
                }
                revertItemPropsState(mappedItems, revertProps);
            }
        } else if (mappedItems.length > 2) {
            throw new Error(
                `ltrRtlMapping "${ltrRtlMapping}" has been found more than twice. They should always come in pair.`
            );
        }
    }

    function revertItemPropsState(items, propsState) {
        const startItemState = items[0].getItemState();
        const endItemState = items[1].getItemState();
        for (const prop of propsState) {
            if (startItemState[prop] !== undefined || endItemState[prop] !== undefined) {
                [endItemState[prop], startItemState[prop]] = [
                    startItemState[prop],
                    endItemState[prop],
                ];
            }
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
            addLtrRtlMappedItem: (item) => {
                if (!ltrRtlMappedItems.has(item.ltrRtlMapping)) {
                    ltrRtlMappedItems.set(item.ltrRtlMapping, [item]);
                } else {
                    ltrRtlMappedItems.get(item.ltrRtlMapping).push(item);
                }
            },
            removeLtrRtlMappedItem: (item) => {
                const mappedItems = ltrRtlMappedItems.get(item.ltrRtlMapping);
                if (!mappedItems) {
                    return;
                }
                if (mappedItems.length === 1) {
                    ltrRtlMappedItems.delete(item.ltrRtlMapping);
                    return;
                }
                const index = mappedItems.indexOf(item);
                if (index !== -1) {
                    mappedItems.splice(index, 1);
                }
            },
            updateLtrRtlMappedItem: handleLtrRtl,
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
/**
 * Registers selectable items to be able to switch their props if needed in some
 * contexts with RTL languages.
 *
 * Many options are selectable components (BuilderButtonGroup or BuilderSelect)
 * with at least a "Left" and a "Right" button, but their action actually
 * depends on the start and end of the line (e.g. `flex-row` vs
 * `flex-row-reverse`). They need some logic to work across all 4 possible
 * combinations of LTR / RTL in the builder and the iframe (LTR-LTR, LTR-RTL,
 * RTL-LTR, RTL-RTL).
 *
 * The place of the button (visually on the left or on the right) depends on the
 * _backend language_: in English, the 1st button is on the left, the 2nd is on
 * the right. In Arabic, the 1st button is on the right, the 2nd is on the left.
 * Similarly, in a dropdown, LTR-speaking people will think of "left" as the 1st
 * element: it comes at the top. But RTL-speaking people will think of "right"
 * as the 1st element: it should come at the top.
 * That is why we need to adapt each button's label, icon, and action.
 *
 * @param {{ ltrRtlMapping: string, isLabelLinkedToContent: boolean, getItemState: Function }}
 */
export function useSelectableLtrRtlComponent({
    ltrRtlMapping,
    isLabelLinkedToContent,
    getItemState = () => {},
}) {
    const env = useEnv();
    if (ltrRtlMapping && env.selectableContext) {
        const ltrRtlMappedItem = {
            ltrRtlMapping,
            isLabelLinkedToContent,
            getItemState,
            langDir: env.langDir,
        };
        env.selectableContext.addLtrRtlMappedItem(ltrRtlMappedItem);

        onWillStart(() => {
            env.selectableContext.updateLtrRtlMappedItem(ltrRtlMappedItem);
        });
        onWillUpdateProps(async () => {
            env.selectableContext.updateLtrRtlMappedItem(ltrRtlMappedItem);
        });
        onWillDestroy(() => {
            env.selectableContext.removeLtrRtlMappedItem(ltrRtlMappedItem);
        });
    }
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

export function useReloadAction(getAllActions) {
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
        return await Promise.all(cleanOrApplyProms);
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
export function useOperationWithReload(callApply, reload) {
    const env = useEnv();
    return async (...args) => {
        const { editingElement } = args[0][0];
        env.services.ui.block();
        try {
            const applyResults = await callApply(...args);
            if (!applyResults.includes(BuilderAction.cancelReload)) {
                env.editor.shared.history.addStep();
                await env.editor.shared.savePlugin.save();
                const url = reload.getReloadUrl?.();
                await env.editor.config.reloadEditor({ url, editingElement });
            }
        } finally {
            env.services.ui.unblock();
        }
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

export function useBuilderNumberInputUnits() {
    const comp = useComponent();
    const env = useEnv();

    /**
     * @param {string | number} values - Values separated by spaces or a number
     * @param {(string) => string} convertSingleValueFn - Convert a single value
     */
    const convertSpaceSplitValues = (values, convertSingleValueFn) => {
        if (typeof values === "number") {
            return convertSingleValueFn(values.toString());
        }
        if (values === null) {
            return values;
        }
        if (!values) {
            return "";
        }
        return values.trim().split(/\s+/g).map(convertSingleValueFn).join(" ");
    };

    const formatRawValue = (rawValue) =>
        convertSpaceSplitValues(rawValue, (value) => {
            const unit = comp.props.unit;
            const { savedValue, savedUnit } = value.match(
                /(?<savedValue>[\d.e+-]+)(?<savedUnit>\w*)/
            ).groups;
            if (savedUnit || comp.props.saveUnit) {
                // Convert value from saveUnit to unit
                value = convertNumericToUnit(
                    parseFloat(savedValue),
                    savedUnit || comp.props.saveUnit,
                    unit,
                    getHtmlStyle(env.getEditingElement().ownerDocument)
                );
            }
            // Put *at most* 3 decimal digits
            return parseFloat(parseFloat(value).toFixed(3)).toString();
        });

    const clampValue = (value) => {
        if (comp.props.composable && !value && value !== 0) {
            return value;
        }
        value = parseFloat(value);
        if (value < comp.props.min) {
            return `${comp.props.min}`;
        }
        if (value > comp.props.max) {
            return `${comp.props.max}`;
        }
        return +value.toFixed(3);
    };

    const parseDisplayValue = (displayValue) => {
        if (!displayValue) {
            return displayValue;
        }
        if (comp.props.composable) {
            displayValue = displayValue
                .trim()
                .replace(/,/g, ".")
                .replace(/[^0-9.-\s]/g, "")
                // Only accept "-" at the start or after a space
                .replace(/(?<!^|\s)-/g, "");
        }
        displayValue =
            displayValue.split(" ").map(clampValue.bind(this)).join(" ") || comp.props.default;
        return convertSpaceSplitValues(displayValue, (value) => {
            if (value === "") {
                return value;
            }
            const unit = comp.props.unit;
            const saveUnit = comp.props.saveUnit;
            const applyWithUnit = comp.props.applyWithUnit;
            if (unit && saveUnit) {
                // Convert value from unit to saveUnit
                value = convertNumericToUnit(
                    value,
                    unit,
                    saveUnit,
                    getHtmlStyle(env.getEditingElement().ownerDocument)
                );
            }
            if (unit && applyWithUnit) {
                if (saveUnit || saveUnit === "") {
                    value = value + saveUnit;
                } else {
                    value = value + unit;
                }
            }
            return value;
        });
    };
    return { formatRawValue, parseDisplayValue, clampValue };
}

/**
 * Handles errors during builder actions.
 * Currently it only checks if the error was triggered on an outdated snippet,
 * and in that case it suppresses the error and shows a notification instead.
 * This function can potentially be extended in the future to handle additional
 * errors and recovery strategies.
 *
 * @param {Error} error - The caught error
 * @param {Element} editingElement - The element being edited
 * @param {Component} comp -  The component
 * @throws {Error} If editingElement is not an outdated snippet
 */
function handleBuilderActionError(error, editingElement, comp) {
    // Check if editingElement belongs to an outdated snippet, and displays a
    // warning notification if yes.
    const isOutdated =
        comp.env.editor.shared.versionError.checkNotifyOutdatedSnippet(editingElement);
    if (!isOutdated) {
        throw error;
    }
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
        return await Promise.all(proms);
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
        try {
            let actionValue = getAction(actionId).getValue({ editingElement, params: actionParam });
            if (actionValue === undefined) {
                actionValue = defaultValue;
            }
            return {
                value: actionValue,
            };
        } catch (error) {
            handleBuilderActionError(error, editingElement, comp);
        }
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
    useLayoutEffect(
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

        comp.env.editor.shared.operation.next(
            async () => {
                try {
                    await fn(actionsSpecs, isPreviewing);
                } catch (error) {
                    handleBuilderActionError(error, comp.env.getEditingElement(), comp);
                }
            },
            {
                load: async () => {
                    try {
                        return await Promise.all(
                            actionsSpecs.map(async (applySpec) => {
                                if (!applySpec.action.has("load")) {
                                    return;
                                }
                                const hasClean = !!applySpec.action.has("clean");
                                if (
                                    !applySpec.loadOnClean &&
                                    _shouldClean(comp, hasClean, isApplied())
                                ) {
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
                        );
                    } catch (error) {
                        handleBuilderActionError(error, comp.env.getEditingElement(), comp);
                    }
                },
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
            if (!isConnectedElement(editingElement)) {
                return false;
            }
            try {
                const isApplied = getAction(actionId).isApplied?.({
                    editingElement,
                    params: actionParam,
                    value: actionValue,
                });
                return comp.props.inverseAction ? !isApplied : isApplied;
            } catch (error) {
                handleBuilderActionError(error, editingElement, comp);
            }
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
