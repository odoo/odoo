import { Component, computed, onWillDestroy, proxy, signal, t, useProps } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useClickableBuilderComponent,
    useDependencyDefinition,
    useItemEnv,
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
        this.selectableItemId = 0;
        this.menuRef = signal.ref();
        this.state = proxy({
            choices: this.props.choices,
            groups: this.props.groups,
            currentlySelected: undefined,
        });
        const updateCurrentlySelected = () =>
            (this.state.currentlySelected = this.getSelectedValue());

        useBuilderComponent(this.props);
        // Allows cleaning the currently selected item when it's needed.
        useSelectableContext({ clean: this.cleanSelection.bind(this) });
        const { removeMenuListeners, onOpened, onClosed } = useSelectMenuHandler(this.menuRef, {
            onNavigatedAway: this.revert.bind(this),
        });
        Object.assign(this, { removeMenuListeners, onOpened, onClosed });
        this.selectableChoices = computed(() =>
            this.flattenChoices(this.state.choices, this.state.groups).sort(
                (a, b) => b.priority - a.priority
            )
        );
        this.choicesByValue = computed(
            () => new Map(this.selectableChoices().map((choice) => [choice.value, choice]))
        );
        // Initialize the selectable items config: The items objects are built
        // so that each item can act as a builder component and manage its own
        // actions and operations.
        this.updateChoices((choices) => {
            for (const choice of choices) {
                choice.attrs ||= {};
                choice.value ||= `${this.selectableItemId++}`;
                choice.props ||= {};
                choice.props.useItemEnv = (env) => useItemEnv(this.getSelection(choice.value), env);
                // Select items need to have an env to get the builder component
                // behaviour (see: `useBuilderComponent()`) which is by default
                // the one from the select.
                choice.env = this.env;
                const clickableChoice = useClickableBuilderComponent(choice.props);
                Object.assign(choice, clickableChoice);
            }
        });

        updateCurrentlySelected();
        useBus(this.env.editorBus, "UPDATE_EDITING_ELEMENT", updateCurrentlySelected);
        // Handle dependencies for select items.
        [...this.selectableChoices()]
            .filter((choice) => choice.props.id)
            .map((choice) => {
                useDependencyDefinition(choice.props, {
                    isActive: () => choice.value === this.getSelectedValue(),
                });
            });
        onWillDestroy(() => {
            this.removeMenuListeners?.();
        });
    }
    updateChoices(callback) {
        callback(this.state.choices);
        this.state.groups.map((group) => ({
            ...group,
            choices: callback(group.choices),
        }));
    }
    flattenChoices(choices, groups) {
        return [...choices, ...groups.flatMap((g) => g.choices || [])];
    }
    getSelection(value) {
        return this.choicesByValue().get(value);
    }
    getSelectedValue() {
        return this.selectableChoices().find((choice) => choice.isApplied())?.value;
    }
    async select(newSelected) {
        this.getSelection(newSelected).operation.commit();
    }
    preview(newSelected) {
        if (newSelected !== this.previewing) {
            this.previewing = newSelected;
            return this.getSelection(newSelected).operation.preview();
        }
    }
    cleanSelection(...args) {
        return this.getSelection(this.state.currentlySelected)?.clean(...args);
    }
    revert() {
        const result = this.getSelection(this.previewing)?.operation.revert();
        this.previewing = undefined;
        return result;
    }
    onNavigated(choice) {
        this.revert();
        this.preview(choice.value);
    }
}
