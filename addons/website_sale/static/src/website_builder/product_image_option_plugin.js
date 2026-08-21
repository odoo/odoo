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
             * Opens the media dialog on the images tab to replace the
             * current product media with a new image
             */
            ChooseMediaAction,
            /*
             * Opens the media dialog on the videos tab to turn the current
             * product media (main image or additional image) into a video
             */
            ChooseVideoMediaAction,
        },
        // The showcase video isn't protected from the generic block-removal
        // overlay the way "t-field" images are (see "removableNodePredicates"
        // in remove_plugin.js): without this, its generic trash icon would
        // remove the DOM node without clearing "video_url" server-side.
        is_unremovable_selectors: ".o_wsale_product_images .media_iframe_video",
    };
}

/*
 * Return the {model, id} of the product/product.image record backing a
 * product media. For images, the "t-field" attributes ("data-oe-model"/
 * "data-oe-id") are set on the media's parent (an inner <img> is generated
 * for the actual display). Videos aren't a real field reference, so they
 * carry "data-wsale-model"/"data-wsale-id" instead: the website editor's
 * generic save logic crashes on any "[data-oe-model]" element that doesn't
 * also have a matching "data-oe-field"/"data-oe-type".
 */
function getMediaRecordInfo(el) {
    const recordEl = el.closest("[data-oe-model], [data-wsale-model]");
    return {
        model: recordEl.dataset.oeModel || recordEl.dataset.wsaleModel,
        id: recordEl.dataset.oeId || recordEl.dataset.wsaleId,
    };
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
        const { model, id } = getMediaRecordInfo(el);
        const params = {
            image_res_model: model,
            image_res_id: id,
            move: value,
        };

        await rpc("/shop/product/resequence-image", params);
    }
}
/*
 * Removes the image in the back-end
 */
export class RemoveMediaAction extends BuilderAction {
    static id = "removeMedia";
    setup() {
        this.reload = {};
    }
    async apply({ editingElement: el }) {
        const { model, id } = getMediaRecordInfo(el);
        if (model === "product.image") {
            // Unlink the "product.image" record as it is not the main product image.
            await this.services.orm.unlink("product.image", [parseInt(id)]);
        } else if (el.matches(".media_iframe_video")) {
            // The main image can't be unlinked: just clear its showcase video.
            await rpc("/shop/product/replace-image-media", {
                image_res_model: model,
                image_res_id: id,
                video_url: false,
            });
        }
        el.remove();
    }
}

/*
 * Opens the media dialog restricted to the images tab to replace the
 * current product media with a new image.
 */
export class ChooseMediaAction extends BuilderAction {
    static id = "chooseMedia";
    static dependencies = ["media_website", "media"];
    setup() {
        // Turning a video back into a plain image changes its DOM structure
        // entirely (see chooseVideoMedia), so that case needs a reload.
        // The dialog must be awaited from "load" (not "apply"): once "reload"
        // is set, "apply" runs behind a blocking "ui.block()" overlay, which
        // would make the dialog look stuck open for as long as it's awaited.
        this.reload = {};
        this.canTimeout = false;
        this.preview = false;
    }
    async load({ editingElement: mediaEl }) {
        if (!mediaEl.matches(".media_iframe_video")) {
            // The generic flow both opens the dialog and applies the DOM
            // swap as part of its own save callback: nothing left to persist
            // afterwards, unlike the video case below.
            await this.dependencies.media_website.replaceMedia(mediaEl, {
                visibleTabs: ["IMAGES"],
                activeTab: "IMAGES",
            });
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
    async apply({ editingElement: mediaEl, loadResult: selectedImage }) {
        if (!mediaEl.matches(".media_iframe_video") || !selectedImage) {
            return BuilderAction.cancelReload;
        }
        const { model, id } = getMediaRecordInfo(mediaEl);
        await rpc("/shop/product/replace-image-media", {
            image_res_model: model,
            image_res_id: id,
            video_url: false,
            attachment_id: selectedImage.id,
        });
    }
}

/*
 * Turns the current product media (the main image or an additional image)
 * into a video.
 */
export class ChooseVideoMediaAction extends BuilderAction {
    static id = "chooseVideoMedia";
    static dependencies = ["media"];
    setup() {
        this.reload = {};
        this.canTimeout = false;
    }
    async load({ editingElement: el }) {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                // Only pass the current video (not an image) as "node": the
                // dialog would otherwise restrict itself to the images tab,
                // based on the image's own field type.
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
        const { model, id } = getMediaRecordInfo(el);
        await rpc("/shop/product/replace-image-media", {
            image_res_model: model,
            image_res_id: id,
            video_url: selectedVideo.embedUrl,
            image_1920: thumbnailData ? thumbnailData.split(",")[1] : null,
        });
    }
}

registry.category("website-plugins").add(ProductImageOptionPlugin.id, ProductImageOptionPlugin);
