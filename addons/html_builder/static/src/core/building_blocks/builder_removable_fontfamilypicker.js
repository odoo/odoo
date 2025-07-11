import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { BuilderFontFamilyPicker } from "@html_builder/core/building_blocks/builder_fontfamilypicker";
import { BuilderButton } from "@html_builder/core/building_blocks/builder_button";
import { getCSSVariableValue } from "@html_builder/utils/utils_css";

export class BuilderRemovableFontFamilyPicker extends BaseOptionComponent {
    static template = "html_builder.BuilderRemovableFontFamilyPicker";
    static props = {
        actionParam: String,
        title: String,
    };
    static components = {
        BuilderFontFamilyPicker,
        BuilderButton,
    };

    setup() {
        super.setup();
        this.state = useDomState(() => {
            return { specified: !!getCSSVariableValue(
                "set-" + this.props.actionParam,
                window.getComputedStyle(this.env.getEditingElement()),
            )};
        });
    }
}
