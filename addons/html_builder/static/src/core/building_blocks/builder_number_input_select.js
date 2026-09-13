import { onMounted, props, signal, t } from "@odoo/owl";
import { BuilderNumberInput } from "./builder_number_input";
import { BuilderInputNumberDropdown } from "./builder_number_input_dropdown";
import { BuilderSelect, builderSelectProps } from "./builder_select";

export class BuilderNumberInputSelect extends BuilderSelect {
    static template = "html_builder.BuilderNumberInputSelect";
    static components = {
        ...super.components,
        BuilderNumberInput,
        BuilderInputNumberDropdown,
    };

    props = props({
        ...builderSelectProps,
        builderAction: t.string(),
        builderActionParam: t.object(),
        isAnySelectItemActive: t.boolean(),
    });

    inputRef = signal.ref();

    setup() {
        this.showNumberInput = signal(!this.props.isAnySelectItemActive);
        this.label = signal("");

        super.setup();

        onMounted(() => {
            this.inputRef().addEventListener("click", (event) => {
                if (event.target.matches("input")) {
                    this.updateShowNumberInput(true);
                }
            });
        });
    }

    updateCurrentLabel() {
        const template = document.createElement("template");
        template.innerHTML = (this.currentLabel ?? "").trim();
        const element = template.content.firstElementChild;

        this.label.set(element?.textContent);
    }

    updateShowNumberInput(value) {
        this.showNumberInput.set(value);
    }

    closeOnClickAway(target) {
        if (!target.matches("input")) {
            this.updateShowNumberInput(!this.props.isAnySelectItemActive);
            return true;
        }
        return false;
    }
}
