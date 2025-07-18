import { ColorPlugin } from "@html_editor/main/font/color_plugin";

export class ForumColorPlugin extends ColorPlugin {
    resources = {
        ...this.resources,
        // Remove toolbar buttons
        toolbar_items: [],
    };
}
