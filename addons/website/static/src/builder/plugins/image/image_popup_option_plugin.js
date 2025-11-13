import { ALIGNMENT_STYLE_PADDING, between, IMAGE_TOOL } from "@html_builder/utils/option_sequence";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { BaseOptionComponent } from "@html_builder/core/utils";

export const POPUP_IMAGE = between(IMAGE_TOOL, ALIGNMENT_STYLE_PADDING);

export class ImagePopUpOptionPlugin extends Plugin {
    static id = "imagePopUpOption";
    static dependencies = [];
    resources = {
        builder_options: [withSequence(POPUP_IMAGE, ImagePopUpOption)],
    };
}

export class ImagePopUpOption extends BaseOptionComponent {
    static template = "website.ImagePopUpOption";
    static selector = "img";
    static exclude = "a img, header img, footer img, .s_image_gallery img";
}

registry.category("website-plugins").add(ImagePopUpOptionPlugin.id, ImagePopUpOptionPlugin);
