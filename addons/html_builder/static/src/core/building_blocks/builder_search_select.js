import { Component, onWillDestroy, props, t } from "@odoo/owl";
import {
    getAllActionsAndOperations,
    revertPreview,
    useBuilderComponent,
    useCanTimeout,
    useDependencyDefinition,
    useDomState,
    useOperationWithReload,
    useReloadAction,
    useWithLoadingEffect,
    useActionInfo,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { _t } from "@web/core/l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";
import { SelectMenu } from "@web/core/select_menu/select_menu";

function selectItemHasPreview(item, getAllActions) {
    const getAction = item.env.editor.shared.builderActions.getAction;
    for (const action of getAllActions()) {
        if (action.actionId && getAction(action.actionId)?.preview === false) {
            return false;
        }
    }
    return (
        item.props.preview === true ||
        (item.props.preview === undefined && item.env.weContext.preview !== false)
    );
}

export function useClickableSelectItem(item) {
    const { getAllActions, callOperation, isApplied } = getAllActionsAndOperations(item);
    const getAction = item.env.editor.shared.builderActions.getAction;

    const { reload } = useReloadAction(getAllActions);
    const applyOperation = item.env.editor.shared.history.makePreviewableAsyncOperation(callApply);

    const operationWithReload = useOperationWithReload(callApply, reload);

    const withLoadingEffect = useWithLoadingEffect(getAllActions);
    const canTimeout = useCanTimeout(getAllActions);

    const operation = {
        commit: () => {
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
            if (selectItemHasPreview(item, getAllActions)) {
                callOperation(applyOperation.preview, {
                    preview: true,
                    operationParams: {
                        cancellable: true,
                        cancelPrevious: () => applyOperation.revert(),
                        canTimeout: canTimeout,
                    },
                });
            }
        },
    };

    function clean(nextApplySpecs, isPreviewing) {
        const proms = [];
        for (const { actionId, actionParam, actionValue } of getAllActions()) {
            for (const editingElement of item.env.getEditingElements()) {
                let nextAction;
                proms.push(
                    getAction(actionId).clean?.({
                        isPreviewing,
                        editingElement,
                        params: actionParam,
                        value: actionValue,
                        dependencyManager: item.env.dependencyManager,
                        selectableContext: item.env.selectableContext,
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
        const cleanOrApplyProms = [];
        const isAlreadyApplied = isApplied();
        for (const applySpec of applySpecs) {
            const hasClean = !!applySpec.clean;
            if (hasClean && isAlreadyApplied) {
                cleanOrApplyProms.push(
                    applySpec.action.clean({
                        isPreviewing,
                        editingElement: applySpec.editingElement,
                        params: applySpec.actionParam,
                        value: applySpec.actionValue,
                        loadResult: applySpec.loadOnClean ? applySpec.loadResult : null,
                        dependencyManager: item.env.dependencyManager,
                        selectableContext: item.env.selectableContext,
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
                        dependencyManager: item.env.dependencyManager,
                        selectableContext: item.env.selectableContext,
                    })
                );
            }
        }
        return await Promise.all(cleanOrApplyProms);
    }

    return {
        clean,
        isApplied,
        priority:
            getAllActions()
                .map(
                    (action) =>
                        getAction(action.actionId).getPriority?.({
                            params: action.actionParam,
                            value: action.actionValue,
                        }) || 0
                )
                .find(Boolean) || 0,
        operation,
    };
}

export class BuilderSearchSelect extends Component {
    static template = "html_builder.BuilderSearchSelect";
    props = props({
        // basicContainerBuilderComponentProps (converted inline)
        id: t.string().optional(),
        applyTo: t.string().optional(),
        preview: t.boolean().optional(),
        inheritedActions: t.array(t.string()).optional(),

        action: t.string().optional(),
        actionParam: t.any().optional(),
        actionValue: t
            .or([
                t.boolean(),
                t.string(),
                t.number(),
                t.literal(null),
                t.array(t.or([t.boolean(), t.string(), t.number()])),
            ])
            .optional(),

        // Shorthand actions.
        classAction: t.any().optional(),
        attributeAction: t.any().optional(),
        dataAttributeAction: t.any().optional(),
        styleAction: t.any().optional(),

        choices: t
            .array(
                t.object({
                    value: t.any().optional(),
                    label: t.string(),
                })
            )
            .optional([]),
        groups: t
            .array(
                t.object({
                    label: t.string().optional(),
                    choices: t.array(
                        t.object({
                            value: t.any().optional(),
                            label: t.string(),
                        })
                    ),
                    section: t.string().optional(),
                })
            )
            .optional([]),
        defaultMessage: t.string().optional(_t("Select an option...")),
    });
    static components = { BuilderComponent, SelectMenu };

    setup() {
        useBuilderComponent();
        const { getAllActions } = getAllActionsAndOperations(this);
        this.index = 0;
        this.choices = this.setChoicesDefaultValues(this.props.choices);
        this.groups = this.props.groups.map((group) => ({
            ...group,
            choices: this.setChoicesDefaultValues(group.choices),
        }));

        this.menuRef = useChildRef();
        this.getAction = this.env.editor.shared.builderActions.getAction;
        this.info = useActionInfo();
        this.info.action = this.info.actionId;
        delete this.info.actionId;
        // Choices are built so that each item can act as a builder component
        // and manage its own actions and operations.
        // TODO: Improve this implementation. Currently, items inherit the
        // select's env/props so they can use component-based hooks
        // (e.g. `getAllActionsAndOperations`). A better approach would be to
        // decouple these hooks from the current component context and have
        // them accept an options object instead.
        this.selectedChoices = [
            ...this.choices,
            ...this.groups.flatMap((g) => g.choices || []),
        ].map((choice, index) => {
            // Action props set on the select are applied to all items
            // and override any corresponding action props defined on
            // the items themselves.
            choice.props = {
                ...choice.props,
                ...Object.fromEntries(Object.entries(this.info).filter(([, value]) => value)),
            };
            choice.env = this.env;
            return {
                ...choice,
                ...useClickableSelectItem(choice),
            };
        });

        const getValue = (el) => {
            const { actionId, actionParam } = getAllActions().find(
                ({ actionId }) => this.getAction(actionId).getValue
            );
            return this.getAction(actionId).getValue({ editingElement: el, params: actionParam });
        };
        this.currentlySelected = getAllActions().length
            ? getValue(this.env.getEditingElement())
            : this.selectedChoices
                  .filter((choice) => choice.isApplied())
                  .sort((a, b) => b.priority - a.priority)[0]?.value;

        // Handle dependencies for select items.
        [...this.selectedChoices]
            .filter((opt) => opt.id)
            .map((opt) => {
                useDependencyDefinition(opt.id, {
                    isActive: () => opt.value === this.currentlySelected,
                });
            });

        this.domState = useDomState((el) => ({ selected: this.currentlySelected }));
        onWillDestroy(() => this.removeListeners?.());
    }
    setChoicesDefaultValues(choices) {
        return choices.map((choice) => ({
            ...choice,
            value: choice.value || `${this.index++}`,
        }));
    }
    getSelection(value) {
        return this.selectedChoices.find((choice) => choice.value === value);
    }
    select(newSelected) {
        this.getSelection(this.currentlySelected)?.clean();
        this.currentlySelected = newSelected;
        this.getSelection(newSelected).operation.commit();
    }
    preview(newSelected) {
        if (this.previewing !== newSelected) {
            this.previewing = newSelected;
            this.getSelection(this.currentlySelected)?.clean();
            this.getSelection(newSelected).operation.preview();
        }
    }
    revert() {
        revertPreview(this.env.editor);
        this.previewing = undefined;
    }
    onOpened() {
        const menuEl = this.menuRef.el;
        if (menuEl) {
            this.removeListeners?.();
            const onNavigatedAway = this.onNavigatedAway.bind(this);
            const onNavigatedBack = this.onNavigatedBack.bind(this);
            menuEl.addEventListener("pointerleave", onNavigatedAway);
            menuEl.addEventListener("pointerenter", onNavigatedBack);
            this.removeListeners = () => {
                delete this.removeListeners;
                menuEl.removeEventListener("pointerleave", onNavigatedAway);
                menuEl.removeEventListener("pointerenter", onNavigatedBack);
            };
        }
    }
    onClosed() {
        this.removeListeners?.();
        this.onNavigatedAway();
    }
    onNavigated(choice) {
        choice ? this.preview(choice.value) : this.revert();
        this.lastPreviewed = undefined;
    }
    onNavigatedAway() {
        if (this.previewing) {
            this.lastPreviewed = this.previewing;
            this.revert();
        }
    }
    onNavigatedBack() {
        if (this.lastPreviewed) {
            this.preview(this.lastPreviewed);
        }
    }
}
