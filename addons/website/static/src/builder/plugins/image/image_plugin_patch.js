import { ImagePlugin } from "@html_builder/core/image_plugin";
import { patch } from "@web/core/utils/patch";

patch(ImagePlugin.prototype, {
    /**
     * `width` and `height` attributes are added to images at render time. They
     * need to be removed from the DOM in edit mode so that they are not saved
     * and stay dynamic.
     * html_editor converts them to inline styles, which is not required in
     * website.
     *
     * @override
     */
    moveSizeAttributesToStyle() {
        for (const img of this.editable.querySelectorAll("img[width], img[height]")) {
            img.removeAttribute("height");
            img.removeAttribute("width");
        }
    },
});
