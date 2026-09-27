import { FontTypePlugin, headingTags } from "@html_editor/main/font/font_type_plugin";

const excludedPowerboxCommands = ["setTagHeading1", "setTagHeading2", "setTagHeading3"];

export class ForumFontTypePlugin extends FontTypePlugin {
    resources = {
        ...this.resources,
        powerbox_items: this.resources.powerbox_items.filter(
            (item) => !excludedPowerboxCommands.includes(item.commandId)
        ),
        font_type_items: this.resources.font_type_items.filter(
            (item) => !headingTags.includes(item.object.tagName.toUpperCase())
        ),
    };
}
