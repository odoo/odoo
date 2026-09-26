import { WithIgnoreItem, builderSelectProps, useBuilderSelect } from "./builder_select";
import { BuilderNumberInput, builderNumberInputProps } from "./builder_number_input";
import { Component, useProps, t, onMounted, proxy } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { BuilderComponent } from "./builder_component";
import { useBus } from "@web/core/utils/hooks";
import { useSelectionCustomInputContext } from "../utils";

export class BuilderNumberSelect extends Component {
    static components = {
        Dropdown,
        BuilderComponent,
        WithIgnoreItem,
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
        this.state = proxy({
            disableOptions: true,
            customMode: false,
        });
        this.autofocusInput = false;
        const { builderSelectState, buttonRef, contentRef, dropdown, rootRef } = useBuilderSelect(
            this.props
        );
        Object.assign(this, { builderSelectState, buttonRef, contentRef, dropdown, rootRef });
        this.getSelectableState = this.env.selectableContext?.getSelectableState;

        useSelectionCustomInputContext([
            {
                actionId: this.numberInputProps.inputAction,
                actionParam: this.numberInputProps.inputActionParam,
            },
        ]);
        // To prevent the dropdown from closing in certain situations (e.g.
        // clicking on the "custom value" input should keep the selection
        // items available), we need to patch the default close behavior.
        const defaultClose = this.dropdown.close.bind(this.dropdown);
        this.dropdown.close = () => {
            if (!this.inputIsClosingDropdown) {
                // Clicking away with a selected option in "custom mode" should
                // show the selection label again instead of the custom input.
                if (this.state.customMode && this.isSelectableItemEnabled()) {
                    this.setCustomMode(false);
                }
                defaultClose();
            }
            this.inputIsClosingDropdown = false;
        };

        onMounted(() => {
            this.state.disableOptions = !this.env.selectableContext.items.length;
            this.setCustomMode(!this.isSelectableItemEnabled());
        });

        useBus(this.env.editorBus, "DOM_UPDATED", () => {
            this.setCustomMode(!this.isSelectableItemEnabled());
        });
    }

    onInputClick() {
        if (!this.state.disableOptions) {
            this.inputIsClosingDropdown = this.dropdown.isOpen;
        }
    }

    onSelectClick() {
        if (!this.autofocusInput) {
            this.autofocusInput = true;
        }
        this.setCustomMode(true);
    }

    isSelectableItemEnabled() {
        // The correct `currentSelectedItem` value is available during the
        // onMounted call (see `useSelectableComponent` > `refreshCurrentItem`).
        return this.getSelectableState().currentSelectedItem?.isApplied();
    }

    setCustomMode(active) {
        this.state.customMode = active;
    }

    get currentLabel() {
        // Provides the label text to use as the selection's input value.
        return new DOMParser()
            .parseFromString(this.builderSelectState.currentLabel, "text/html")
            .body.textContent?.trim();
    }
}
