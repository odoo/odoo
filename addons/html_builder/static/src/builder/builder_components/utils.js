import { isTextNode } from "@html_editor/utils/dom_info";
import {
    Component,
    EventBus,
    onMounted,
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
import { useDebounced } from "@web/core/utils/timing";

export function useDomState(getState) {
    const env = useEnv();
    const state = useState(getState(env.getEditingElement()));
    useBus(env.editorBus, "STEP_ADDED", () => {
        Object.assign(state, getState(env.getEditingElement()));
    });
    return state;
}

export class BuilderComponent extends Component {
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
        useBus(this.env.dependencyManager, "dependency-updated", () => {
            this.state.isVisible = isVisible();
        });
        if (this.props.dependencies?.length) {
            const listener = () => {
                this.state.isVisible = isVisible();
            };
            this.env.dependencyManager.addEventListener("dependency-updated", listener);
            onWillDestroy(() => {
                this.env.dependencyManager.removeEventListener("dependency-updated", listener);
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
export function useDependencyDefinition({ id, ...item }) {
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

export function useSelectableComponent(id, { onItemChange } = {}) {
    useBuilderComponent();
    const selectableItems = [];
    const refreshCurrentItemDebounced = useDebounced(refreshCurrentItem, 0);
    let currentSelectedItem;
    const env = useEnv();
    const selectableBus = new EventBus();

    function refreshCurrentItem() {
        let currentItem;
        let itemPriority = 0;
        for (const selectableItem of selectableItems) {
            if (selectableItem.isActive() && selectableItem.priority >= itemPriority) {
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
        useDependencyDefinition({
            id,
            type: "select",
            getSelectableItems: () => selectableItems.slice(0),
        });
    }

    onMounted(refreshCurrentItem);
    useBus(env.editorBus, "STEP_ADDED", (ev) => {
        if (ev.detail.isPreviewing) {
            return;
        }
        refreshCurrentItem();
    });
    useBus(selectableBus, "BEFORE_CALL_ACTIONS", () => {
        if (currentSelectedItem) {
            currentSelectedItem.clean();
        }
    });

    const selectableContext = {
        selectableBus,
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
        getSelectedItem: () => currentSelectedItem,
    };
    return selectableContext;
}
export function useSelectableItemComponent(id, { getLabel = () => {} } = {}) {
    const { state, operation, isActive, getActions, priority, clean } =
        useClickableBuilderComponent();
    const env = useEnv();

    let isSelectableActive = isActive;
    if (env.selectableContext) {
        isSelectableActive = () => {
            return env.selectableContext.getSelectedItem() === selectableItem;
        };

        const selectableItem = {
            isActive,
            priority,
            getLabel,
            clean,
            getActions,
        };

        env.selectableContext.addSelectableItem?.(selectableItem);
        onMounted(env.selectableContext.update);
        onWillDestroy(() => {
            env.selectableContext.removeSelectableItem?.(selectableItem);
        });
    }

    if (id) {
        useDependencyDefinition({
            id: id,
            isActive: isSelectableActive,
            getActions,
            selectableBus: env.selectableContext?.selectableBus,
        });
    }

    return { state, operation };
}
export function useClickableBuilderComponent() {
    useBuilderComponent();
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

    function clean() {
        for (const { actionId, actionParam, actionValue } of getAllActions()) {
            for (const editingElement of comp.env.getEditingElements()) {
                getAction(actionId).clean?.({
                    editingElement,
                    param: actionParam,
                    value: actionValue,
                    dependencyManager: comp.env.dependencyManager,
                });
            }
        }
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
        comp.env.selectableContext?.selectableBus.trigger("BEFORE_CALL_ACTIONS");
        const buses = comp.props.inheritedActions
            .map((actionId) => comp.env.dependencyManager.get(actionId).selectableBus)
            .filter(Boolean);
        for (const selectableBus of new Set(buses)) {
            selectableBus.trigger("BEFORE_CALL_ACTIONS");
        }
        let shouldClean = shouldToggle && isActive();
        shouldClean = comp.props.inverseAction ? !shouldClean : shouldClean;
        for (const applySpec of applySpecs) {
            if (shouldClean) {
                applySpec.clean({
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
        const inheritedActions = comp.props.inheritedActions
            .map(
                (actionId) =>
                    comp.env.dependencyManager
                        // The dependency might not be loaded yet.
                        .get(actionId)
                        ?.getActions?.() || []
            )
            .flat();

        return actions.concat(inheritedActions);
    }
    function isActive() {
        const editingElements = comp.env.getEditingElements();
        if (!editingElements.length) {
            return;
        }
        const areActionsActiveTabs = getAllActions().map((o) => {
            const { actionId, actionParam, actionValue } = o;
            // TODO isActive === first editing el or all ?
            const editingElement = editingElements[0];
            const isActive = getAction(actionId).isActive?.({
                editingElement,
                param: actionParam,
                value: actionValue,
            });
            return comp.props.inverseAction ? !isActive : isActive;
        });
        // If there is no `isActive` method for the widget return false
        if (areActionsActiveTabs.every((el) => el === undefined)) {
            return false;
        }
        // If `isActive` is explicitly false for an action return false
        if (areActionsActiveTabs.some((el) => el === false)) {
            return false;
        }
        // `isActive` is true for at least one action
        return true;
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
        state,
        operation,
        isActive,
        clean,
        priority: getPriority(),
        getActions: getAllActions,
    };
}
export function useInputBuilderComponent() {
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
            // TODO try to remove it. We need to move hook in BuilderComponent
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

export const basicContainerBuilderComponentProps = {
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
export const defaultBuilderComponentProps = {
    inheritedActions: [],
};
