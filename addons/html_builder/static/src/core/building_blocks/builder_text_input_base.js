import { useProps } from "@odoo/owl";
import { BuilderInputBase, textInputBaseProps } from "./builder_input_base";

export class BuilderTextInputBase extends BuilderInputBase {
    static template = "html_builder.BuilderTextInputBase";

    props = useProps(textInputBaseProps);
}
