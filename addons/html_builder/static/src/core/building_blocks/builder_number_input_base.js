import { props, t } from "@odoo/owl";
import { BuilderInputBase } from "./builder_input_base";

export class BuilderNumberInputBase extends BuilderInputBase {
    static template = "html_builder.BuilderNumberInputBase";
    props = props({
        // BuilderInputBase props (converted inline)
        slots: t.object().optional(),
        inputRef: t.function().optional(),
        // textInputBasePassthroughProps (converted inline)
        action: t.string().optional(),
        placeholder: t.string().optional(),
        title: t.string().optional(),
        style: t.string().optional(),
        tooltip: t.string().optional(),
        classes: t.string().optional(),
        inputClasses: t.string().optional(),
        prefix: t.string().optional(),
        prefixIcon: t.string().optional(),
        selectTextOnFocus: t.boolean().optional(),

        commit: t.function(),
        preview: t.function(),
        onFocus: t.function().optional(),
        onInput: t.function().optional(),
        onChange: t.function().optional(),
        onKeydown: t.function().optional(),
        onBeforeInput: t.function().optional(),
        value: t.or([t.string(), t.literal(null)]).optional(),

        onKeydownArrow: t.function().optional(),
        clampValue: t.function(),
        composable: t.boolean().optional(false),
        min: t.number().optional(),
        max: t.number().optional(),
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
