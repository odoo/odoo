import { BuilderInputBase } from "./builder_input_base";

export class BuilderNumberInputBase extends BuilderInputBase {
    static template = "html_builder.BuilderNumberInputBase";
    static props = {
        ...super.props,
        clampValue: { type: Function, optional: false },
        composable: { type: Boolean, optional: true },
        min: { type: Number, optional: true },
        max: { type: Number, optional: true },
        step: { type: Number, optional: true },
    };
    static defaultProps = {
        composable: false,
    };

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
            e.target.value = values.join(" ");
            this.props.preview(e.target.value);
        }
        this.props.onKeydown?.(e);
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
