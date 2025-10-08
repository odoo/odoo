import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { getImageSrc } from "@html_editor/utils/image";
import { loadImage } from "@html_editor/utils/image_processing";

export class EmailImagePlugin extends Plugin {
    static id = "image";
    resources = {
        load_reference_content_handlers: () => this.loadImages(this.config.reference),
    };

    /**
     * Return promises for every image to control when they have their final
     * rendered dimensions.
     * Background images do not influence their content dimensions so they don't
     * have to be waited for.
     */
    loadImages(root) {
        const promises = [];
        for (const img of root.querySelectorAll("img")) {
            promises.push(loadImage(getImageSrc(img)));
        }
        return promises;
    }

    /**
     * <i>/<span> fa + circle should be centered properly when the icon is converted into an image
     *
     */
    // TODO EGGMAIL: fontToImg
}

registry.category("mail-html-conversion-plugins").add(EmailImagePlugin.id, EmailImagePlugin);
