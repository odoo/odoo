import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { BOX_BORDER_SHADOW } from "../option_sequence";
import { registry } from "@web/core/registry";
import { BaseVerticalAlignmentOption } from "@html_builder/plugins/base_vertical_alignment_option";

export class WebsiteVerticalAlignmentOption extends BaseVerticalAlignmentOption {
    static selector = ".s_attributes_vertical_col";
    static applyTo = ":scope > .row";
    level = 0;
    justify = false;
}

class VerticalAlignmentOptionPlugin extends Plugin {
    static id = "websiteVerticalAlignmentOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [withSequence(BOX_BORDER_SHADOW, WebsiteVerticalAlignmentOption)],
    };
}
registry
    .category("website-plugins")
    .add(VerticalAlignmentOptionPlugin.id, VerticalAlignmentOptionPlugin);
