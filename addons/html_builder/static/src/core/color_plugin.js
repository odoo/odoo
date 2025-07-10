import { ColorPlugin as EditorColorPlugin } from "@html_editor/main/font/color_plugin";
import { getAllUsedColors } from "@html_builder/utils/utils_css";

export class ColorPlugin extends EditorColorPlugin {
    getUsedCustomColors(mode) {
        return getAllUsedColors(this.editable);
    }
}
