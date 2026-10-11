import { usePlugin } from "@odoo/owl";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseProductPageAction } from "./product_page_option_plugin";

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
             * Replaces the video in the back-end
             */
            ReplaceVideoAction,
        },
        content_not_editable_selectors: ".o_wsale_product_images [data-embedded='video']",
        reload_context_processors: withSequence(20, this.keepMediaSelected.bind(this)),
        on_editor_started_handlers: this.showSelectedSlide.bind(this),
    };

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
    }

    keepMediaSelected(context, editingElement) {
        const mediaId = editingElement?.closest("[data-oe-model='product.image']")?.dataset.oeId;
        if (mediaId) {
            context.selector = `[data-oe-model='product.image'][data-oe-id='${mediaId}']`
                + ":not(.o_carousel_product_indicators *) > *";
        }
        return context;
    }

    showSelectedSlide() {
        const selector = this.config.reloadContext?.selector;
        const mediaEl = selector && this.editable.querySelector(selector);
        const slideEl = mediaEl?.closest("#o-carousel-product .carousel-item");
        if (slideEl) {
            const carouselEl = slideEl.closest(".carousel");
            const index = [...slideEl.parentElement.children].indexOf(slideEl);
            this.bootstrap.getOrCreateInstance(this.window.Carousel, carouselEl).to(index);
        }
    }
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
            image_res_id: el.parentElement.dataset.oeId,
            move: value,
            product_variant_id: this.document.querySelector('[data-product-variant-id]').dataset.productVariantId,
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
        const wrapper = el.closest("[data-oe-model='product.image']");
        if (wrapper) {
            await this.services.orm.unlink("product.image", [parseInt(wrapper.dataset.oeId)]);
            wrapper.remove();
        } else {
            el.remove();
        }
    }
}
/*
 * Replaces the video in the back-end
 */
export class ReplaceVideoAction extends BaseProductPageAction {
    static id = "replaceVideo";
    static dependencies = [...super.dependencies, "media"];
    setup() {
        super.setup();
        this.canTimeout = false;
    }
    async load({ editingElement: el }) {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                node: el,
                visibleTabs: ["VIDEOS"],
                save: (videoEl, [video]) => resolve(video),
            });
            onClose.then(() => resolve());
        });
    }
    async apply({ editingElement: el, loadResult: video }) {
        if (!video) {
            return BuilderAction.cancelReload;
        }
        const wrapper = el.closest("[data-oe-model='product.image']");
        await this.services.orm.write(
            "product.image",
            [parseInt(wrapper.dataset.oeId)],
            await this.getVideoValues(video)
        );
    }
}

registry.category("website-plugins").add(ProductImageOptionPlugin.id, ProductImageOptionPlugin);
