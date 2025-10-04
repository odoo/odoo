import { POPUP_IMAGE } from "@html_builder/utils/option_sequence";
import { registry } from "@web/core/registry";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";

export class ImagePopUpOptionPlugin extends Plugin {
    static id = "imagePopUpOption";
    static dependencies = [];
    resources = {
        builder_options: [
            withSequence(POPUP_IMAGE, {
                template: "website.ImagePopUpOption",
                selector: "img",
                exclude: "a img, header img, footer img, .s_image_gallery img",
            }),
        ],
    };
}

registry.category("website-plugins").add(ImagePopUpOptionPlugin.id, ImagePopUpOptionPlugin);
