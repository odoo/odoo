import { builderSelectProps, useBuilderSelect, builderSelectComponents } from "./builder_select";
import { BuilderNumberInput, builderNumberInputProps } from "./builder_number_input";
import { Component, useProps, t, onMounted, signal } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";
import { convertParamToObject } from "../utils";
import { useEnv, useSubEnv } from "@web/owl2/utils";

export class BuilderNumberSelect extends Component {
    static components = {
        ...builderSelectComponents,
        BuilderNumberInput,
    };
    static template = "html_builder.BuilderNumberSelect";

    props = useProps(builderSelectProps);
    // All basic builder component props are available to the inner builder
    // select. We only provide one action for the input: `inputAction`, which
    // can be either a core action or a custom action [extending a core one].
    numberInputProps = useProps({
        ...builderNumberInputProps,
        inputAction: t.string().optional(),
        inputActionParam: t.any().optional(),
    });

    setup() {
        this.customMode = signal(false);
        this.autofocusInput = false;
        const { builderSelectLabel, buttonRef, contentRef, dropdown, rootRef } = useBuilderSelect(
            this.props
        );
        Object.assign(this, { builderSelectLabel, buttonRef, contentRef, dropdown, rootRef });
        this.getSelectableState = this.env.selectableContext.getSelectableState;

        const env = useEnv();
        const getAction = env.editor.shared.builderActions.getAction;

        const numberInputProps = this.numberInputProps;
        function customInputClean(isPreviewing) {
            const { inputAction, inputActionParam } = numberInputProps;
            if (!inputAction) {
                return;
            }
            const action = getAction(inputAction);
            const proms = [];
            for (const editingElement of env.getEditingElements()) {
                proms.push(
                    action.clean?.({
                        isPreviewing,
                        editingElement,
                        params: convertParamToObject(inputActionParam),
                        dependencyManager: env.dependencyManager,
                    })
                );
            }
            return Promise.all(proms);
        }

        useSubEnv({
            selectionCustomInputContext: { customInputClean },
        });

        // Avoid opening an empty menu.
        const defaultOpen = this.dropdown.open.bind(this.dropdown);
        this.dropdown.open = () => {
            if (this.contentRef()?.querySelector(".o-hb-select-dropdown-item")) {
                defaultOpen();
            }
        };

        // To prevent the dropdown from closing in certain situations (e.g.
        // clicking on the "custom value" input should keep the selection items
        // available), we need to patch the default close behavior.
        const defaultClose = this.dropdown.close.bind(this.dropdown);
        this.dropdown.close = () => {
            if (!this.preventCloseOnInputClick) {
                // Clicking away with a selected option in "custom mode" should
                // show the selection label again instead of the custom input.
                if (this.customMode() && this.isSelectableItemEnabled()) {
                    this.customMode.set(false);
                }
                defaultClose();
            }
            this.preventCloseOnInputClick = false;
        };

        onMounted(() => {
            // Wait for child select items to register so the applied preset is
            // known.
            this.customMode.set(!this.isSelectableItemEnabled());
        });

        useBus(this.env.editorBus, "DOM_UPDATED", () => {
            this.customMode.set(!this.isSelectableItemEnabled());
        });
    }

    onInputClick() {
        if (this.dropdown.isOpen) {
            this.preventCloseOnInputClick = true;
        }
    }

    onLabelClick() {
        if (!this.autofocusInput) {
            this.autofocusInput = true;
        }
        this.customMode.set(true);
    }

    isSelectableItemEnabled() {
        return this.getSelectableState().currentSelectedItem?.isApplied();
    }

    get currentLabel() {
        // Provides the label text to use as the selection's input value.
        return new DOMParser()
            .parseFromString(this.builderSelectLabel(), "text/html")
            .body.textContent?.trim();
    }
}
