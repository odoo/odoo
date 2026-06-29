import { Component, onWillDestroy, proxy, signal, t, useProps } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    getApplyToElements,
    useBuilderComponent,
    useClickableBuilderComponent,
    useDependencyDefinition,
    useItemEnv,
    useLtrRtlHandler,
    useSelectableContext,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { _t } from "@web/core/l10n/translation";
import { useBus } from "@web/core/utils/hooks";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useSelectMenuHandler } from "./select_many2x";

const CHOICES_SCHEMA = t
    .array(
        t.object({
            value: t.any().optional(),
            label: t.string(),
        })
    )
    .optional([]);

export class BuilderSearchSelect extends Component {
    static template = "html_builder.BuilderSearchSelect";
    props = useProps({
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
        choices: CHOICES_SCHEMA,
        groups: t
            .array(
                t.object({
                    label: t.string().optional(),
                    choices: CHOICES_SCHEMA,
                    section: t.string().optional(),
                })
            )
            .optional([]),
        defaultMessage: t.string().optional(_t("Select an option...")),
    });
    static components = { BuilderComponent, SelectMenu };

    setup() {
        useBuilderComponent(this.props);
        useSelectableContext({ clean: this.cleanSelection.bind(this) });
        this.menuRef = signal.ref();
        Object.assign(
            this,
            useSelectMenuHandler(this.menuRef, {
                onNavigatedAway: this.onNavigatedAway.bind(this),
                onNavigatedBack: this.onNavigatedBack.bind(this),
            })
        );

        this.index = 0;
        this.state = proxy({ choices: [], groups: [], selected: undefined });

        const { addLtrRtlMappedItem, updateLtrRtlMappedItem } = useLtrRtlHandler();
        this.addLtrRtlMappedItem = addLtrRtlMappedItem;
        this.updateLtrRtlMappedItem = updateLtrRtlMappedItem;

        // Initialize the select items main config.
        this.initialChoices = this.props.choices;
        this.initialGroups = this.props.groups;
        this.updateAllChoices(this.setupChoices.bind(this));
        this.updateAllChoices(this.adaptLtrRtlChoices.bind(this));
        // Choices are built so that each item can act as a builder component
        // and manage its own actions and operations.
        this.updateAllChoices(this.buildClickableChoices.bind(this));
        this.updateChoices(this.updateEditingElements.bind(this));
        useBus(this.env.editorBus, "UPDATE_EDITING_ELEMENT", () =>
            this.updateChoices(this.updateEditingElements.bind(this))
        );
        // Handle dependencies for select items.
        [...this.selectableChoices]
            .filter((choice) => choice.props.id)
            .map((choice) => {
                useDependencyDefinition(choice.props, {
                    isActive: () => choice.value === this.currentlySelected,
                });
            });
        onWillDestroy(() => {
            this.removeMenuListeners?.();
        });
    }
    setupChoices(choices) {
        for (const choice of choices) {
            choice.attrs ||= {};
            choice.value ||= `${this.index++}`;
            choice.props ||= {};
            choice.itemPropsState = proxy({
                ...choice.props,
                title: choice.attrs.title,
                label: choice.label,
            });
            if (choice.props.ltrRtlMapping) {
                choice.ltrRtlConfig = {
                    ltrRtlMapping: choice.props.ltrRtlMapping,
                    isLabelLinkedToContent: choice.props.isLabelLinkedToContent,
                    getItemState: () => choice.itemPropsState,
                    langDir: this.env.langDir,
                };
                this.addLtrRtlMappedItem(choice.ltrRtlConfig);
            }
            choice.props.useItemEnv = (env) => useItemEnv(this.getSelection(choice.value), env);
        }
        return choices;
    }
    buildClickableChoices(choices) {
        for (const choice of choices) {
            // Select items need to have an env to get the builder component
            // behaviour (see: `useBuilderComponent()`) which is by default
            // the one from the select.
            choice.env = this.env;
            const clickableChoice = useClickableBuilderComponent(choice.props);
            Object.assign(choice, clickableChoice);
        }
    }
    updateEditingElements(choices) {
        return choices
            .map((choice) => {
                // Update target elements to support `applyTo` for the
                // select component items.
                const oldEnv = choice.env;
                const applyTo = choice.props.applyTo;
                // No item-level `applyTo`: use the same target as
                // the select, even if it defines its own `applyTo`.
                const els = this.env.getEditingElements();
                const editingElements = applyTo ? getApplyToElements(els, applyTo) : els;
                choice.env = {
                    ...oldEnv,
                    editor: oldEnv.editor,
                    getEditingElements: () => editingElements,
                    getEditingElement: () => editingElements[0],
                };
                return choice;
            })
            .filter((choice) => choice.env.getEditingElement());
    }
    adaptLtrRtlChoices(choices) {
        for (const choice of choices) {
            if (choice.props.ltrRtlMapping) {
                const defaultPropsState = {
                    ...choice.props,
                    title: choice.attrs.title,
                    label: choice.label,
                };
                this.updateLtrRtlMappedItem(choice.ltrRtlConfig);
                // Update the select item values.
                choice.props = {
                    ...choice.props,
                    ...choice.itemPropsState,
                };
                choice.attrs.title = choice.itemPropsState.title;
                choice.label = choice.itemPropsState.label;
                // Reset `itemPropsState` to ensure subsequent item
                // adaptations use the original props state rather
                // than the updated one.
                choice.itemPropsState = defaultPropsState;
            }
        }
    }
    updateAllChoices(callback) {
        return {
            choices: callback(this.initialChoices),
            groups: this.initialGroups.map((group) => ({
                ...group,
                choices: callback(group.choices),
            })),
        };
    }
    flattenChoices(choices, groups) {
        return [...choices, ...groups.flatMap((g) => g.choices || [])];
    }
    updateChoices(callback) {
        const { choices, groups } = this.updateAllChoices(callback);
        this.state.choices = choices;
        this.state.groups = groups;
        this.selectableChoices = this.flattenChoices(this.state.choices, this.state.groups);
        this.currentlySelected = this.getSelectedValue();
        this.state.selected = this.currentlySelected;
    }
    getSelection(value) {
        const choices =
            this.selectableChoices || this.flattenChoices(this.initialChoices, this.initialGroups);
        return choices.find((choice) => choice.value === value);
    }
    getSelectedValue() {
        return this.selectableChoices
            .filter((choice) => choice.isApplied())
            .sort((a, b) => b.priority - a.priority)[0]?.value;
    }
    async select(newSelected) {
        this.getSelection(newSelected).operation.commit();
    }
    preview(newSelected) {
        if (newSelected !== this.previewing) {
            this.previewing = newSelected;
            this.getSelection(newSelected).operation.preview();
        }
    }
    cleanSelection(...args) {
        this.getSelection(this.currentlySelected)?.clean(...args);
    }
    revert() {
        this.getSelection(this.previewing)?.operation.revert();
        this.previewing = undefined;
    }
    onNavigated(choice) {
        this.revert();
        this.preview(choice.value);
        this.lastPreviewed = undefined;
    }
    onNavigatedAway() {
        this.lastPreviewed = this.previewing;
        this.revert();
    }
    onNavigatedBack() {
        if (this.lastPreviewed) {
            this.preview(this.lastPreviewed);
        }
    }
}
