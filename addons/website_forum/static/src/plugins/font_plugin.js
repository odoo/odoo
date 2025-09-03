import { FontPlugin } from "@html_editor/main/font/font_plugin";

const excludedPowerboxCommands = ["setTagHeading1", "setTagHeading2", "setTagHeading3"];
const excludedFontItems = ["h1", "h2", "h3"];

export class ForumFontPlugin extends FontPlugin {
    resources = {
        ...this.resources,
        powerbox_items: this.resources.powerbox_items.filter(
            (item) => !excludedPowerboxCommands.includes(item.commandId)
        ),
        // Remove font-size selector from toolbar
        toolbar_items: this.resources.toolbar_items.filter(
            (item) => item.object.id !== "font-size"
        ),
        font_items: this.resources.font_items.filter(
            (item) => !excludedFontItems.includes(item.object.tagName)
        ),
    };
}
