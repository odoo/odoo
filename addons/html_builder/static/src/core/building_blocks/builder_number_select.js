import { WithIgnoreItem, builderSelectProps, useBuilderSelect } from "./builder_select";
import { BuilderNumberInput, builderNumberInputProps } from "./builder_number_input";
import { Component, useProps, t, onMounted, proxy } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { BuilderComponent } from "./builder_component";
import { useSubEnv } from "@web/owl2/utils";

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
        this.getAction = this.env.editor.shared.builderActions.getAction;
        Object.assign(
            this,
            useBuilderSelect(this.props, {
                onSelect: () => {
                    // ...
                    this.state.enableCustomValue = false;
                },
            })
        );
        this.getSelectableState = this.env.selectableContext?.getSelectableState;

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

        useSubEnv({
            inputContext: { clean: this.clean.bind(this) },
        });

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
        return this.getSelectableState().currentSelectedItem?.isApplied();
    }

    clean(isPreviewing) {
        const proms = [];
        for (const editingElement of this.env.getEditingElements()) {
            proms.push(
                this.getAction(this.numberInputProps.inputAction).clean?.({
                    isPreviewing,
                    editingElement,
                    params: this.numberInputProps.inputActionParam,
                    dependencyManager: this.env.dependencyManager,
                })
            );
        }
        return Promise.all(proms);
    }

    get currentLabel() {
        // ...
        return new DOMParser()
            .parseFromString(this.builderSelectState.currentLabel, "text/html")
            .body.textContent?.trim();
    }
}
