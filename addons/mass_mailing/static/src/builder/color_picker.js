import { BuilderColorPicker } from "@html_builder/core/building_blocks/builder_colorpicker";

export class MassMailingColorPicker extends BuilderColorPicker {
    static defaultProps = {
        ...BuilderColorPicker.defaultProps,
        colorPrefix: "",
    };
}
