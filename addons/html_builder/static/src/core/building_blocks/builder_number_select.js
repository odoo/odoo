import { WithIgnoreItem, builderSelectProps, useBuilderSelect } from "./builder_select";
import { BuilderNumberInput, builderNumberInputProps } from "./builder_number_input";
import { Component, useProps, t, onMounted, proxy } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { BuilderComponent } from "./builder_component";

export class BuilderNumberSelect extends Component {
    static components = {
        Dropdown,
        BuilderComponent,
        WithIgnoreItem,
        BuilderNumberInput,
    };
    static template = "html_builder.BuilderNumberSelect";

    props = useProps(builderSelectProps);
    // ...
    numberInputProps = useProps({
        ...builderNumberInputProps,
        inputAction: t.string().optional(),
        inputActionParam: t.any().optional(),
    });

    setup() {
        this.state = proxy({
            disableOptions: true,
            enableCustomValue: false,
        });
        Object.assign(
            this,
            useBuilderSelect(this.props, {
                onSelect: () => {
                    // ...
                    this.state.enableCustomValue = false;
                },
            })
        );
        this.selectableState = this.env.selectableContext?.getSelectableState;

        // ...
        const defaultClose = this.dropdown.close.bind(this.dropdown);
        this.dropdown.close = () => {
            // ...
            if (!this.inputIsClosingDropdown) {
                if (this.state.enableCustomValue && this.isSelectableItemEnabled()) {
                    this.state.enableCustomValue = false;
                }
                defaultClose();
            }
            this.inputIsClosingDropdown = false;
        };

        onMounted(() => {
            this.state.disableOptions = !this.env.selectableContext.items.length;
            this.state.enableCustomValue = !this.isSelectableItemEnabled();
        });
    }

    onInputClick() {
        if (!this.state.disableOptions) {
            this.inputIsClosingDropdown = this.dropdown.isOpen;
        }
    }

    onSelectClick() {
        this.state.enableCustomValue = true;
    }

    isSelectableItemEnabled() {
        // ...
        return this.selectableState().currentSelectedItem?.isApplied();
    }

    get currentLabel() {
        // ...
        return new DOMParser()
            .parseFromString(this.builderSelectState.currentLabel, "text/html")
            .body.textContent?.trim();
    }
}
