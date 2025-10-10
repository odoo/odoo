import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { getImageSrc } from "@html_editor/utils/image";
import { loadImage } from "@html_editor/utils/image_processing";

export class EmailImagePlugin extends Plugin {
    static id = "EmailImagePlugin";
    resources = {
        load_reference_content_handlers: this.loadImages.bind(this),
    };

    /**
     * Return promises for every image to control when they have their final
     * rendered dimensions.
     * Background images do not influence their content dimensions so they don't
     * have to be waited for.
     */
    loadImages({ root }) {
        const promises = [];
        for (const img of root.querySelectorAll("img")) {
            promises.push(loadImage(getImageSrc(img)));
        }
        return promises;
    }
}

registry.category("mail-html-conversion-plugins").add(EmailImagePlugin.id, EmailImagePlugin);
