import { ColorUIPlugin as EditorColorUIPlugin } from "@html_editor/main/font/color_ui_plugin";
import { getAllUsedColors } from "@html_builder/utils/utils_css";

export class ColorUIPlugin extends EditorColorUIPlugin {
    getUsedCustomColors(mode) {
        return getAllUsedColors(this.editable);
    }

    getPropsForColorSelector(type) {
        const props = { ...super.getPropsForColorSelector(type) };
        props.cssVarColorPrefix = "hb-cp-";
        return props;
    }
}
