import { BuilderInputSelectBase } from "@html_builder/core/building_blocks/builder_input_select_base";
import { BuilderTextInput } from "@html_builder/core/building_blocks/builder_text_input";
import { pick } from "@web/core/utils/objects";

export class BuilderInputSelectText extends BuilderInputSelectBase {
    static template = "html_builder.BuilderInputSelectText";
    static components = { ...BuilderInputSelectBase.components, BuilderTextInput };
    static props = {
        ...BuilderTextInput.props,
        ...BuilderInputSelectBase.props,
    };

    get inputSelectTextProps() {
        return {
            ...pick(this.props, ...Object.keys(BuilderTextInput.props)),
            selectTextOnFocus: true,
        };
    }
}
