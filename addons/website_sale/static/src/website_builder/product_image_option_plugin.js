import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";
import { getDataURLFromFile } from "@web/core/utils/urls";

export class ProductImageOptionPlugin extends Plugin {
    static id = "productImageOption";
    resources = {
        builder_actions: {
            /*
             * Change sequence of product page images
             */
            SetPositionAction,
            /*
             * Removes the image in the back-end
             */
            RemoveMediaAction,
            /*
             * Opens the media dialog on the images tab to replace the current product
             * media with a new image
             */
            ChooseImageAction,
            /*
             * Opens the media dialog on the videos tab to turn the current product media
             * (an existing image or video) into a video
             */
            ChooseVideoAction,
        },
    };
}

/*
 * Resolve the element carrying the identifying attributes of the "product.image" record
 * backing a product media (main or additional image/video).
 */
function getProductImageWrapper(el) {
    return el.closest("[data-oe-model='product.image'], [data-wsale-image-id]");
}

/*
 * Resolve the id of the "product.image" record from its wrapper. For images, the "t-field"
 * attributes ("data-oe-id") are set on the media's parent (an inner <img> is generated for
 * the actual display). Videos aren't a "t-field", so they carry "data-wsale-image-id"
 * directly on themselves instead.
 */
function getProductImageId(el) {
    const wrapper = getProductImageWrapper(el);
    return parseInt(wrapper.dataset.wsaleImageId || wrapper.dataset.oeId);
}

/*
* Change sequence of product page images
*/
export class SetPositionAction extends BuilderAction {
    static id = "setPosition";
    setup() {
        this.reload = {};
    }
    async apply({ editingElement: el, value }) {
        const params = {
            image_res_id: getProductImageId(el),
            move: value,
            product_variant_id: this.document.querySelector('[data-product-variant-id]').dataset.productVariantId,
        };

        await rpc("/shop/product/resequence-image", params);
    }
}
/*
 * Removes the image (or video) in the back-end
 */
export class RemoveMediaAction extends BuilderAction {
    static id = "removeMedia";
    setup() {
        this.reload = {};
    }
    async apply({ editingElement: el }) {
        const wrapper = getProductImageWrapper(el);
        if (wrapper) {
            await this.services.orm.unlink("product.image", [getProductImageId(el)]);
            wrapper.remove();
        } else {
            el.remove();
        }
    }
}

/*
 * Opens the media dialog restricted to the images tab to replace the current product media
 * (an existing image or video) with a new image.
 */
export class ChooseImageAction extends BuilderAction {
    static id = "chooseImage";
    static dependencies = ["media_website", "media"];
    setup() {
        // Turning a video back into a plain image changes its DOM structure entirely (see
        // ChooseVideoAction), so that case needs a reload. The dialog must be awaited from
        // "load" (not "apply"): once "reload" is set, "apply" runs behind a blocking
        // "ui.block()" overlay, which would make the dialog look stuck open for as long as
        // it's awaited.
        this.reload = {};
        this.canTimeout = false;
        this.preview = false;
    }
    async load({ editingElement: el }) {
        if (!el.matches(".media_iframe_video")) {
            // The generic flow both opens the dialog and applies the DOM swap as part of its
            // own save callback: nothing left to persist afterwards, unlike the video case
            // below.
            await this.dependencies.media_website.replaceMedia(el);
            return null;
        }
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                visibleTabs: ["IMAGES"],
                save: async (elements, selectedMedia) => resolve(selectedMedia[0]),
            });
            onClose.then(() => resolve());
        });
    }
    async apply({ editingElement: el, loadResult: selectedImage }) {
        if (!el.matches(".media_iframe_video") || !selectedImage) {
            return BuilderAction.cancelReload;
        }
        await rpc("/shop/product/replace-image-media", {
            image_id: getProductImageId(el),
            attachment_id: selectedImage.id,
        });
    }
}

/*
 * Turns the current product media (an existing image or video) into a video.
 */
export class ChooseVideoAction extends BuilderAction {
    static id = "chooseVideo";
    static dependencies = ["media"];
    setup() {
        this.reload = {};
        this.canTimeout = false;
    }
    async load({ editingElement: el }) {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                // Only pass the current video (not an image) as "node": the dialog would
                // otherwise restrict itself to the images tab, based on the image's own
                // field type.
                node: el.matches(".media_iframe_video") ? el : undefined,
                visibleTabs: ["VIDEOS"],
                save: async (elements, selectedMedia) => resolve(selectedMedia[0]),
            });
            onClose.then(() => resolve());
        });
    }
    async apply({ editingElement: el, loadResult: selectedVideo }) {
        if (!selectedVideo) {
            return BuilderAction.cancelReload;
        }
        let thumbnailData = null;
        if (selectedVideo.thumbnailUrl) {
            const response = await fetch(selectedVideo.thumbnailUrl);
            const blob = await response.blob();
            thumbnailData = await getDataURLFromFile(blob);
        }
        await rpc("/shop/product/replace-image-media", {
            image_id: getProductImageId(el),
            video_url: selectedVideo.embedUrl,
            image_1920: thumbnailData ? thumbnailData.split(",")[1] : null,
        });
    }
}

registry.category("website-plugins").add(ProductImageOptionPlugin.id, ProductImageOptionPlugin);
