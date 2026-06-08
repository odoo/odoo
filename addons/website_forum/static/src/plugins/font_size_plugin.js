import { FontSizePlugin } from "@html_editor/main/font/font_size_plugin";

export class ForumFontSizePlugin extends FontSizePlugin {
    resources = {
        ...this.resources,
        // Remove font size selector from toolbar.
        toolbar_items: [],
    };
}
