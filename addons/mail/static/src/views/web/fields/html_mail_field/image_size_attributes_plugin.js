import { Plugin } from "@html_editor/plugin";

export class ImageSizeAttributesPlugin extends Plugin {
    static id = "imageSizeAttributes";
    /** @type {import("plugins").EditorResources} */
    resources = {
        html_compatibility_processors: this.moveImageSizeAttributesToStyle.bind(this),
    };

    /**
     * During `convert_inline`, image elements may receive `width` and `height`
     * attributes, along with inline styles. These attributes force specific
     * dimensions, which breaks the fallback to default sizing. We move them to
     * the inline style to allow proper resizing behavior. The attributes will
     * be re-applied on save.
     *
     * @param {HTMLElement} root
     * @returns {HTMLElement}
     */
    moveImageSizeAttributesToStyle(root) {
        for (const img of root.querySelectorAll("img[width], img[height]")) {
            for (const attribute of ["width", "height"]) {
                const value = img.getAttribute(attribute);
                img.removeAttribute(attribute);
                if (value) {
                    img.style.setProperty(attribute, isNaN(value) ? value : `${value}px`);
                }
            }
        }
        return root;
    }
}
