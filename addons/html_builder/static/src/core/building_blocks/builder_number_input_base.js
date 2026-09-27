import { t, useProps } from "@odoo/owl";
import { BuilderInputBase, textInputBaseProps } from "./builder_input_base";

export class BuilderNumberInputBase extends BuilderInputBase {
    static template = "html_builder.BuilderNumberInputBase";

    props = useProps({
        ...textInputBaseProps,
        clampValue: t.function(),
        composable: t.boolean().optional(false),
        max: t.number().optional(),
        min: t.number().optional(),
        onKeydownArrow: t.function().optional(),
        step: t.number().optional(),
    });

    onKeydown(e) {
        if (["ArrowUp", "ArrowDown"].includes(e.key)) {
            // Prevent default behavior of input number since we want to
            // debounce commit for the history
            e.preventDefault();
            const step = this.props.step || 1;
            const values = e.target.value.split(" ").map((number) => parseFloat(number) || 0);
            values.forEach((value, i) => {
                values[i] = this.props.clampValue(value + (e.key === "ArrowUp" ? step : -step));
            });
            this.state.value = values.join(" ");
            e.target.value = this.state.value;
            this.props.preview(e.target.value);
            this.props.onKeydownArrow?.(e);
        } else {
            super.onKeydown(...arguments);
        }
    }

    onBeforeInput(e) {
        if (!this.props.composable) {
            return;
        }

        // We prevent the input if the user write an invalid char in the input.
        // If the user paste an incorrect input, it will be fixed when parsing
        // the input after.
        if (!e.data || e.data.length !== 1 || /[0-9\-.,\s]/.test(e.data)) {
            return;
        }

        e.preventDefault();
    }
}
