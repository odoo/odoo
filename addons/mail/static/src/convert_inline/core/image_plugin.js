import { registry } from "@web/core/registry";
import { Plugin } from "../plugin";
import { getImageSrc } from "@html_editor/utils/image";
import { loadImage } from "@html_editor/utils/image_processing";

export class ImagePlugin extends Plugin {
    static id = "image";
    static dependencies = ["measurementSnapshot"];
    resources = {
        on_load_reference_content_handlers: () => this.loadImages(this.config.reference),
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
            const src = getImageSrc(img);
            if (src) {
                promises.push(loadImage(src, img));
            }
        }
        return Promise.allSettled(promises);
    }

    /**
     * TODO EGGMAIL: WORKING HERE find a way to generalize the layout building functions
     * so that it does not require direct access to referenceNode, and it can build everything
     * from facts.
     * Register everything needed into facts
     * => the EmailNode should output the image properly instead of the element with the .fa class
     */

    /**
     * can get computedStyle, ::before
     * can get dimensions directly without needing fit-content stuff
     * can get font-size directly
     * background capture required
     *
     * need to add an argument to getComputedStyle and check
     * all usages with 2 args
     * add the argument to all derived function? -> maybe
     * not necessary, as usage is pretty niche, and it's
     * always best to use getComputedStyle anyways
     *
     * all transformations should happen before constraints propagation
     * the Emailnode entity should be properly classified as an img
     * check if the resulting img should be handled as a normal
     * img or if it requires exceptions
     * include the spacing in the final image, use the combination of
     * dimensions + font-size to get the proper spacing
     */
    /**
     * <i>/<span> fa + circle should be centered properly when the icon is converted into an image
     *
     */
    // TODO EGGMAIL: fontToImg

    // TODO EGGMAIL:
    // case study: background color + color filter => should apply the same logic as a normal
    // filter? => if the logic is to create a new attachment. If it uses browser rendering
    // capabilities, then it won't work
    // issue: the filter is currently an external div with position: absolute
}

registry.category("mail-html-conversion-core-plugins").add(ImagePlugin.id, ImagePlugin);
