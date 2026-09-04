import { isElement, isTextNode } from "@html_editor/utils/dom_info";
import { convertNumericToUnit, getHtmlStyle } from "@html_editor/utils/formatting";
import {
    onMounted,
    onWillDestroy,
    onWillStart,
    onWillUpdateProps,
    proxy,
    t,
    toRaw,
    useEffect,
    useListener,
    useScope,
} from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { useEnv, useSubEnv } from "@web/owl2/utils";
import { BuilderAction } from "./builder_action";

/**
 * @typedef {{
 *  actionId: number;
 *  actionParam: any;
 *  actionValue: string;
 * }} BuilderCustomAction
 * @typedef {typeof basicContainerBuilderComponentProps} DefaultBuilderProps
 * @typedef {import("@html_editor/editor").EditorContext} EditorContext
 * @typedef {((reload_context: Object, editingElement: Element) => reload_context)[]} reload_context_processors
 */

// Selectors for special cases where snippet options are bound to parent
// containers instead of the snippet itself.
export const BLOCKQUOTE_PARENT_HANDLERS = ".s_reviews_wall .row > div";
export const CARD_PARENT_HANDLERS =
    ".s_three_columns .row > div, .s_comparisons .row > div, .s_cards_grid .row > div, .s_cards_soft .row > div, .s_product_list .row > div, .s_newsletter_centered .row > div, .s_company_team_spotlight .row > div, .s_comparisons_horizontal .row > div, .s_company_team_grid .row > div, .s_company_team_card .row > div, .s_carousel_cards_item, .s_features_cards .row > div";
export const SPECIAL_CARD_SELECTOR = `div:is(${CARD_PARENT_HANDLERS}) > .s_card`;

/**
 * @param {Element} el
 */
function isElementConnected(el) {
    return el && el.isConnected && !!el.ownerDocument.defaultView;
}

/**
 * @template T
 * @param {() => T} getState
 * @param {{ checkEditingElement?: boolean }} [options]
 */
export function useDomState(getState, { checkEditingElement = true } = {}) {
    const scope = useScope();
    const env = useEnv();
    const isValid = (el) => (!el && !checkEditingElement) || isElementConnected(el);
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
                if (!isValid(editingElement) || scope.isDestroyed()) {
                    return;
                }
                throw e;
            }
        }
    };
    /** @type {T} */
    const state = proxy({});
    onWillStart(() => handler());
    useListener(env.editorBus, "DOM_UPDATED", handler);
    return state;
}

/**
 * @param {DefaultBuilderProps} props
 * @param {{ raw?: boolean }} [options]
 */
export function useActionInfo(props, options) {
    /**
     * @param {keyof DefaultBuilderProps} paramName
     */
    function getParam(paramName) {
        let value = props[paramName];
        if (value === undefined) {
            // 'null' can be used as a value
            value = weContext[paramName];
        }
        return !options?.raw && typeof value === "object" ? JSON.stringify(value) : value;
    }

    const { weContext } = useEnv();
    return {
        actionId: props.action || weContext.action,
        actionParam: getParam("actionParam"),
        actionValue: props.actionValue,
        classAction: getParam("classAction"),
        styleAction: getParam("styleAction"),
        styleActionValue: props.styleActionValue,
        attributeAction: getParam("attributeAction"),
        attributeActionValue: props.attributeActionValue,
        dataAttributeAction: getParam("dataAttributeAction"),
        dataAttributeActionValue: props.dataAttributeActionValue,
    };
}

/**
 * Updates/returns the items environment when a builder component's items are
 * props objects rather than sub-components.
 *
 * @param {object} item
 * @param {object} extension
 */
export function useItemEnv(item, extension) {
    if (extension) {
        const itemEnv = Object.create(item.env);
        const descrs = Object.getOwnPropertyDescriptors(extension);
        const env = Object.freeze(Object.defineProperties(itemEnv, descrs));
        item.env = env;
    }
    return item?.env || {};
}

/**
 * Sets up the `selectableContext` required for options to correctly handle
 * selectable items, which may be managed differently by each component.
 *
 * @param {{
 *  add?: () => void;
 *  remove?: () => void;
 *  clean?: () => void;
 *  [key: string]: any;
 * }} params
 */
export function useSelectableContext({ add, remove, clean, ...config } = {}) {
    useSubEnv({
        selectableContext: {
            addSelectableItem: add,
            removeSelectableItem: remove,
            cleanSelectedItem: clean,
            ...config,
        },
    });
}

/**
 * Returns the new component's editing elements defined by the applyTo selector.
 *
 * @param {HTMLElement[]} els The default editing elements.
 * @param {string} applyTo
 */
export function getApplyToElements(els, applyTo) {
    const elSet = new Set();
    for (const editingEl of els) {
        for (const child of editingEl.querySelectorAll(applyTo)) {
            elSet.add(child);
        }
    }
    return [...elSet];
}

/**
 * @param {DefaultBuilderProps} props
 */
export function useBuilderComponent(props) {
    function updateEditingElements() {
        /** @type {HTMLElement[]} */
        const els = oldEnv.getEditingElements();
        if (applyTo) {
            editingElements = getApplyToElements(els, applyTo);
        } else {
            editingElements = els;
        }
    }

    const newEnv = {};
    const oldEnv = useEnv();
    let editingElements;
    let applyTo = props.applyTo;
    updateEditingElements();
    useListener(oldEnv.editorBus, "UPDATE_EDITING_ELEMENT", updateEditingElements);
    onWillUpdateProps(async (nextProps) => {
        if (props.applyTo !== nextProps.applyTo) {
            applyTo = nextProps.applyTo;
            oldEnv.editorBus.trigger("UPDATE_EDITING_ELEMENT");
            await oldEnv.triggerDomUpdated();
        }
    });
    newEnv.getEditingElements = () => editingElements;
    newEnv.getEditingElement = () => editingElements[0];
    const weContext = {};
    for (const key in basicContainerBuilderComponentProps) {
        const value = props[key];
        if (value !== undefined) {
            weContext[key] = value;
        }
    }
    if (Object.keys(weContext).length) {
        newEnv.weContext = { ...oldEnv.weContext, ...weContext };
    }
    if (!oldEnv.langDir) {
        newEnv.langDir = {
            content: oldEnv.editor.config.isEditableRTL ? "rtl" : "ltr",
            builder: localization.direction,
        };
    }
    // Some component items are plain props objects rather than Owl
    // components (e.g. `BuilderSearchSelect`). Since `useSubEnv` only
    // works with components, those objects cannot inherit the parent
    // environment automatically. In that case, we update their `env`
    // manually here.
    props.useItemEnv ? props.useItemEnv(newEnv) : useSubEnv(newEnv);
}

/**
 * @param {DefaultBuilderProps} props
 * @param {any} item
 * @param {{ onReady?: Promise }} [options]
 */
export function useDependencyDefinition(props, item, { onReady } = {}) {
    const env = useEnv();
    const scope = useScope();
    const ignore = env.ignoreBuilderItem;
    if (onReady) {
        onReady.then(() => {
            if (!scope.isDestroyed()) {
                env.dependencyManager.add(props.id, item, ignore);
            }
        });
    } else {
        env.dependencyManager.add(props.id, item, ignore);
    }

    onWillDestroy(() => {
        if (scope.status === 1 /* mounted/started */) {
            env.dependencyManager.removeByValue(item);
        } else {
            // A component destroyed before being mounted was cancelled by a
            // new render of an ancestor, which usually recreates a
            // replacement that re-registers the same dependency, but
            // asynchronously. Removing the dependency right away would make
            // dependents observe a transient hole and flip their state back
            // and forth on each recreation, up to an infinite render loop:
            // keep serving this entry until the replacement supersedes it.
            env.dependencyManager.retireByValue(item);
        }
    });
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

export function useLtrRtlHandler() {
    const ltrRtlMappedItems = new Map();

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

    return {
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
    };
}

/**
 * @param {DefaultBuilderProps} props
 * @param {{ onItemChange?: (item: any) => any }} [options]
 */
export function useSelectableComponent(props, { onItemChange } = {}) {
    useBuilderComponent(props);
    const selectableItems = [];
    const refreshCurrentItemDebounced = useDebounced(refreshCurrentItem, 0, { immediate: true });
    const env = useEnv();

    const state = proxy({
        currentSelectedItem: null,
    });

    const { addLtrRtlMappedItem, removeLtrRtlMappedItem, updateLtrRtlMappedItem } =
        useLtrRtlHandler();

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

    if (props.id) {
        useDependencyDefinition(props, {
            type: "select",
            getSelectableItems: () => selectableItems.slice(0),
        });
    }

    onMounted(refreshCurrentItem);
    useListener(env.editorBus, "DOM_UPDATED", refreshCurrentItem);

    useSelectableContext({
        add: (item) => {
            selectableItems.push(item);
        },
        remove: (item) => {
            const index = selectableItems.indexOf(item);
            if (index !== -1) {
                selectableItems.splice(index, 1);
            }
        },
        clean: (...args) => {
            if (state.currentSelectedItem) {
                return state.currentSelectedItem.clean(...args);
            }
        },
        update: refreshCurrentItemDebounced,
        items: selectableItems,
        refreshCurrentItem: () => refreshCurrentItem(),
        getSelectableState: () => state,
        addLtrRtlMappedItem,
        removeLtrRtlMappedItem,
        updateLtrRtlMappedItem,
    });
}

/**
 * @param {DefaultBuilderProps} props
 * @param {{ getLabel?: () => any }} [options]
 */
export function useSelectableItemComponent(props, { getLabel = () => {} } = {}) {
    const { operation, isApplied, getActions, priority, clean, onReady } =
        useClickableBuilderComponent(props);
    const env = useEnv();

    let isSelectableActive = isApplied;
    let state;
    if (env.selectableContext) {
        const selectableState = env.selectableContext.getSelectableState();
        isSelectableActive = () => {
            env.selectableContext.refreshCurrentItem();
            return (
                toRaw(selectableState.currentSelectedItem) === selectableItem ||
                (props.id && selectableState.currentSelectedItem?.id === props.id)
            );
        };

        const selectableItem = {
            isApplied,
            priority,
            getLabel,
            clean,
            getActions,
            id: props.id,
        };

        env.selectableContext.addSelectableItem(selectableItem);
        state = proxy({
            isActive: false,
        });
        useEffect(() => {
            state.isActive =
                toRaw(selectableState.currentSelectedItem) === selectableItem ||
                (props.id && selectableState.currentSelectedItem?.id === props.id);
        });
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

    if (props.id) {
        useDependencyDefinition(
            props,
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
 * @param {{
 *  ltrRtlMapping: string;
 *  isLabelLinkedToContent: boolean;
 *  getItemState: () => any;
 * }} params
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

/**
 * @param {() => Iterable<BuilderCustomAction>} getAllActions
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
            await Promise.all(
                asyncActions.map((obj) =>
                    obj.action.prepare({ ...obj.descr, editingElement: env.getEditingElement() })
                )
            );
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
                        editingElement: env.getEditingElement(),
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
 * @param {() => Iterable<BuilderCustomAction>} getAllActions
 */
export function useReloadAction(getAllActions) {
    const env = useEnv();
    const getAction = env.editor.shared.builderActions.getAction;
    let reload = null;
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
 * @param {DefaultBuilderProps} props
 * @param {() => Iterable<BuilderCustomAction>} getAllActions
 */
export function hasPreview(props, getAllActions) {
    const env = useEnv();
    const getAction = env.editor.shared.builderActions.getAction;

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
        (props.preview === true || (props.preview === undefined && env.weContext.preview !== false))
    );
}

/**
 * @param {() => Iterable<BuilderCustomAction>} getAllActions
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
 * @param {() => Iterable<BuilderCustomAction>} getAllActions
 */
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

/**
 * @param {DefaultBuilderProps} props
 */
export function useClickableBuilderComponent(props) {
    useBuilderComponent(props);
    const env = props.useItemEnv?.() || useEnv();
    const { getAllActions, callOperation, isApplied } = getAllActionsAndOperations(props);
    const getAction = env.editor.shared.builderActions.getAction;

    const onReady = usePrepareAction(getAllActions);
    const { reload } = useReloadAction(getAllActions);

    const applyOperation = env.editor.shared.history.makePreviewableAsyncOperation(callApply);
    const inheritedActionIds = props.inheritedActions || env.weContext.inheritedActions || [];

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
            revertPreview(env.editor);
        },
    };

    if (!hasPreview(props, getAllActions)) {
        operation.preview = () => {};
    }

    function clean(nextApplySpecs, isPreviewing) {
        const proms = [];
        for (const { actionId, actionParam, actionValue } of getAllActions()) {
            for (const editingElement of env.getEditingElements()) {
                let nextAction;
                proms.push(
                    getAction(actionId).clean?.({
                        isPreviewing,
                        editingElement,
                        params: actionParam,
                        value: actionValue,
                        dependencyManager: env.dependencyManager,
                        selectableContext: env.selectableContext,
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
        await env.selectableContext?.cleanSelectedItem(applySpecs, isPreviewing);
        const cleans = inheritedActionIds
            .map((actionId) => env.dependencyManager.get(actionId).cleanSelectedItem)
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
            const shouldClean = _shouldClean(env, props, hasClean, isAlreadyApplied);
            if (shouldClean) {
                cleanOrApplyProms.push(
                    applySpec.action.clean({
                        isPreviewing,
                        editingElement: applySpec.editingElement,
                        params: applySpec.actionParam,
                        value: applySpec.actionValue,
                        loadResult: applySpec.loadOnClean ? applySpec.loadResult : null,
                        dependencyManager: env.dependencyManager,
                        selectableContext: env.selectableContext,
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
                        dependencyManager: env.dependencyManager,
                        selectableContext: env.selectableContext,
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

/**
 * @template {(...args: any[]) => any} T
 * @param {T} callApply
 * @param {{ getReloadUrl?: () => string }} reload
 * @returns {T}
 */
export function useOperationWithReload(callApply, reload) {
    const env = useEnv();
    const ui = useService("ui");
    return async (...args) => {
        const { editingElement } = args[0][0];
        ui.block();
        try {
            const applyResults = await callApply(...args);
            if (!applyResults.includes(BuilderAction.cancelReload)) {
                env.editor.shared.history.commit();
                await env.editor.shared.savePlugin.save();
                const url = reload.getReloadUrl?.();
                await env.editor.config.reloadEditor({ url, editingElement });
            }
        } finally {
            ui.unblock();
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

/**
 * @param {DefaultBuilderProps} props
 */
export function useBuilderNumberInputUnits(props) {
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
            const unit = props.unit;
            const { savedValue, savedUnit } = value.match(
                /(?<savedValue>[\d.e+-]+)(?<savedUnit>\w*)/
            ).groups;
            if (savedUnit || props.saveUnit) {
                // Convert value from saveUnit to unit
                value = convertNumericToUnit(
                    parseFloat(savedValue),
                    savedUnit || props.saveUnit,
                    unit,
                    getHtmlStyle(env.getEditingElement().ownerDocument)
                );
            }
            // Put *at most* 3 decimal digits
            return parseFloat(parseFloat(value).toFixed(3)).toString();
        });

    const clampValue = (value) => {
        if (props.composable && !value && value !== 0) {
            return value;
        }
        value = parseFloat(value);
        if (value < props.min) {
            return `${props.min}`;
        }
        if (value > props.max) {
            return `${props.max}`;
        }
        return +value.toFixed(3);
    };

    const parseDisplayValue = (displayValue) => {
        if (!displayValue) {
            return displayValue;
        }
        if (props.composable) {
            displayValue = displayValue
                .trim()
                .replace(/,/g, ".")
                .replace(/[^0-9.-\s]/g, "")
                // Only accept "-" at the start or after a space
                .replace(/(?<!^|\s)-/g, "");
        }
        displayValue =
            displayValue.split(" ").map(clampValue.bind(this)).join(" ") || props.default;
        return convertSpaceSplitValues(displayValue, (value) => {
            if (value === "") {
                return value;
            }
            const unit = props.unit;
            const saveUnit = props.saveUnit;
            const applyWithUnit = props.applyWithUnit;
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
 * @param {Error} error
 * @param {import("@web/env").OdooEnv} env
 * @param {Element} [editingElement]
 * @throws {Error} If editingElement is not an outdated snippet
 */
function handleBuilderActionError(error, env, editingElement) {
    editingElement ||= env.getEditingElement();
    // Check if editingElement belongs to an outdated snippet, and displays a
    // warning notification if yes.
    const isOutdated = env.editor.shared.versionError.checkNotifyOutdatedSnippet(editingElement);
    if (!isOutdated) {
        throw error;
    }
}

/**
 * @param {DefaultBuilderProps} props
 * @param {{
 *  defaultValue?: any;
 *  formatRawValue?: (rawValue: any) => string;
 *  parseDisplayValue?: (displayValue: string) => any;
 * }} options
 * @returns
 */
export function useInputBuilderComponent(
    props,
    {
        defaultValue,
        formatRawValue = (rawValue) => rawValue,
        parseDisplayValue = (displayValue) => displayValue,
    } = {}
) {
    /**
     * @param {Iterable} applySpecs
     * @param {boolean} isPreviewing
     */
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
                    dependencyManager: env.dependencyManager,
                })
            );
        }
        return await Promise.all(proms);
    }

    /**
     * @param {string} userInputValue
     */
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

    /**
     * @param {Element} editingElement
     */
    async function getState(editingElement) {
        await onReady;
        if (!isElementConnected(editingElement)) {
            // TODO try to remove it. We need to move hook in BuilderComponent
            return {};
        }
        const value = getValueFromDom(editingElement);
        // When no value could be computed (a swallowed action error, e.g. an
        // outdated snippet), leave the state empty rather than populating
        // `value: undefined`: the dependency getValue() below keys its DOM
        // fallback on `"value" in state`, so a spurious `value` key would
        // disarm it.
        return value === undefined ? {} : { value };
    }

    /**
     * @param {Element} editingElement
     */
    function getValueFromDom(editingElement) {
        const actionWithGetValue = getAllActions().find(
            ({ actionId }) => getAction(actionId).getValue
        );
        const { actionId, actionParam } = actionWithGetValue;
        try {
            const actionValue = getAction(actionId).getValue({
                editingElement,
                params: actionParam,
            });
            return actionValue === undefined ? defaultValue : actionValue;
        } catch (error) {
            handleBuilderActionError(error, env, editingElement);
        }
    }

    /**
     * @param {string} userInputValue
     */
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

    const env = useEnv();
    const { getAllActions, callOperation } = getAllActionsAndOperations(props);
    const getAction = env.editor.shared.builderActions.getAction;
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

    const applyOperation = env.editor.shared.history.makePreviewableAsyncOperation(callApply);
    const operationWithReload = useOperationWithReload(callApply, reload);

    const shouldPreview = hasPreview(props, getAllActions);

    if (props.id) {
        useDependencyDefinition(
            props,
            {
                type: "input",
                getValue: () => {
                    // state is populated asynchronously: until then, compute
                    // the value from the DOM, so that a component recreated
                    // after being cancelled (destroyed before being mounted)
                    // doesn't transiently expose `undefined` to dependents.
                    if ("value" in state) {
                        return state.value;
                    }
                    const editingElement = env.getEditingElement();
                    return isElementConnected(editingElement)
                        ? getValueFromDom(editingElement)
                        : undefined;
                },
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
 * @param {import("@odoo/owl").Signal<HTMLElement>} ref
 */
export function useApplyVisibility(ref) {
    /**
     * @param {boolean} hasContent
     */
    function applyVisibility(hasContent) {
        ref()?.classList.toggle("d-none", !hasContent);
    }
    return applyVisibility;
}

/**
 * @param {import("@odoo/owl").Signal<HTMLElement>} contentRef
 * @param {(hasContent: boolean) => any} callback
 */
export function useVisibilityObserver(contentRef, callback) {
    function applyVisibility() {
        const hasContent = [...contentRef().childNodes].some(
            (el) =>
                (isTextNode(el) && el.textContent !== "") ||
                (isElement(el) && !el.classList.contains("d-none"))
        );
        callback(hasContent);
    }

    const observer = new MutationObserver(applyVisibility);
    useEffect(() => {
        // Tracked read: re-observes (after the cleanup below disconnects) when
        // the ref signal changes, including when it is populated on mount.
        const contentEl = contentRef();
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
    });
}

/**
 * @param {import("@odoo/owl").Signal<HTMLInputElement>} ref
 * @param {(value: string) => string} commit
 */
export function useInputDebouncedCommit(ref, commit) {
    return useDebounced(() => {
        const normalizedDisplayValue = commit(ref().value);
        ref().value = normalizedDisplayValue;
    }, 550);
    // ↑ 500 is the delay when holding keydown between the 1st and 2nd event
    // fired. Some additional delay by the browser may add another ~5-10ms.
    // We debounce above that threshold to keep a single history commit when
    // holding up/down on a number or range input.
}

/**
 * @param {DefaultBuilderProps} props
 */
export function getAllActionsAndOperations(props) {
    function getActionsSpecs(actions, userInputValue) {
        const getAction = env.editor.shared.builderActions.getAction;
        const overridableMethods = ["apply", "clean", "load", "loadOnClean"];
        const specs = [];
        for (let { actionId, actionParam, actionValue } of actions) {
            const action = getAction(actionId);
            // Take the action value defined by the clickable or the input given
            // by the user.
            actionValue = actionValue === undefined ? userInputValue : actionValue;
            for (const editingElement of env.getEditingElements()) {
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
            const actionParam = env.weContext[actionId] || props[actionId];
            if (actionParam !== undefined) {
                actions.push({
                    actionId,
                    actionParam: convertParamToObject(actionParam),
                    actionValue: props[actionValue],
                });
            }
        }
        return actions;
    }

    function getCustomAction() {
        const actionId = props.action || env.weContext.action;
        if (actionId) {
            const actionParam = props.actionParam ?? env.weContext.actionParam;
            return {
                actionId: actionId,
                actionParam: convertParamToObject(actionParam),
                actionValue: props.actionValue,
            };
        }
    }

    function getAllActions() {
        const actions = getShorthandActions();
        const { actionId, actionParam, actionValue } = getCustomAction() || {};
        if (actionId) {
            actions.push({ actionId, actionParam, actionValue });
        }
        const inheritedActionIds = props.inheritedActions || env.weContext.inheritedActions || [];
        const inheritedActions = inheritedActionIds.flatMap(
            // The dependency might not be loaded yet.
            (actionId) => env.dependencyManager.get(actionId)?.getActions?.() || []
        );
        return actions.concat(inheritedActions);
    }

    function callOperation(fn, params = {}) {
        const isPreviewing = !!params.preview;
        const actionsSpecs = getActionsSpecs(getAllActions(), params.userInputValue);

        env.editor.shared.operation.next(
            async () => {
                try {
                    await fn(actionsSpecs, isPreviewing);
                } catch (error) {
                    handleBuilderActionError(error, env);
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
                                    _shouldClean(env, props, hasClean, isApplied())
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
                        handleBuilderActionError(error, env);
                    }
                },
                ...params.operationParams,
            }
        );
    }

    function isApplied() {
        const getAction = env.editor.shared.builderActions.getAction;
        const editingElements = env.getEditingElements();
        if (!editingElements.length) {
            return;
        }
        const areActionsActiveTabs = getAllActions().map((o) => {
            const { actionId, actionParam, actionValue } = o;
            // TODO isApplied === first editing el or all ?
            const editingElement = editingElements[0];
            if (!isElementConnected(editingElement)) {
                return false;
            }
            try {
                const isApplied = getAction(actionId).isApplied?.({
                    editingElement,
                    params: actionParam,
                    value: actionValue,
                });
                return props.inverseAction ? !isApplied : isApplied;
            } catch (error) {
                handleBuilderActionError(error, env);
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

    const env = useEnv();

    return {
        getAllActions,
        callOperation,
        isApplied,
    };
}

function _shouldClean(env, props, hasClean, isApplied) {
    if (!hasClean) {
        return false;
    }
    const shouldToggle = !env.selectableContext;
    const shouldClean = shouldToggle && isApplied;
    return props.inverseAction ? !shouldClean : shouldClean;
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

export const basicContainerBuilderComponentProps = {
    action: t.string().optional(),
    actionParam: t.any().optional(),
    applyTo: t.string().optional(),
    id: t.string().optional(),
    inheritedActions: t.array(t.string()).optional(),
    preview: t.boolean().optional(),

    // Shorthand actions.
    attributeAction: t.any().optional(),
    classAction: t.any().optional(),
    dataAttributeAction: t.any().optional(),
    styleAction: t.any().optional(),
};

export const clickableBuilderComponentProps = {
    ...basicContainerBuilderComponentProps,
    actionValue: t
        .or([
            t.boolean(),
            t.string(),
            t.number(),
            t.literal(null),
            t.array(t.or([t.boolean(), t.string(), t.number()])),
        ])
        .optional(),
    inheritedActions: t.array(t.string()).optional(),
    inverseAction: t.boolean().optional(),

    // Shorthand actions values.
    attributeActionValue: t.or([t.string(), t.array(), t.literal(null)]).optional(),
    classActionValue: t.or([t.string(), t.array(), t.literal(null)]).optional(),
    dataAttributeActionValue: t.or([t.string(), t.array(), t.literal(null)]).optional(),
    styleActionValue: t.or([t.string(), t.array(), t.literal(null)]).optional(),
};
