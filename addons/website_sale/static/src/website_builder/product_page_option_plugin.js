import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { ProductPageOption } from "./product_page_option";
import { rpc } from "@web/core/network/rpc";
import { isImageCorsProtected } from "@html_editor/utils/image";
import { WebsiteConfigAction, PreviewableWebsiteConfigAction } from "@website/builder/plugins/customize_website_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";
import wSaleUtils from "@website_sale/js/website_sale_utils";

class ProductPageOptionPlugin extends Plugin {
    static id = "productPageOption";
    static dependencies = ["builderActions", "media", "customizeWebsite"];
    static shared = ["forceCarouselRedraw"];
    resources = {
        builder_options: ProductPageOption,
        builder_actions: {
            ProductPageContainerWidthAction,
            ProductPageContainerOrderAction,
            ProductPageImageWidthAction,
            ProductPageImageRatioAction,
            ProductPageImageRatioMobileAction,
            ProductPageImageLayoutAction,
            ProductPageImageRoundnessAction,
            ProductPageImageGridSpacingAction,
            ProductPageImageGridColumnsAction,
        },
        clean_for_save_handlers: ({ root: el }) => {
            // TODO the content of this clean_for_save_handlers should probably
            // be a generic thing for the whole editor.

            // Make sure that if the user removes the whole text of the
            // breadcrumb, it is restored to the default value.
            if (
                // TODO the "placeholder" feature should be reviewed, this is
                // not a valid HTML attribute.
                el.getAttribute("placeholder")
                && el.hasAttribute("data-oe-zws-empty-inline")
                && /^[\s\u200b]*$/.test(el.textContent)
            ) {
                el.textContent = el.getAttribute("placeholder");
            }

            const mainEl = el.querySelector(ProductPageOption.selector);
            if (!mainEl) {
                return;
            }
            const productDetailMain = mainEl.querySelector("#product_detail_main");
            if (!productDetailMain) {
                return;
            }
            const accordionEl = productDetailMain.querySelector("#product_accordion");
            if (!accordionEl) {
                return;
            }

            const accordionItemsEls = accordionEl.querySelectorAll(".accordion-item");
            accordionItemsEls.forEach((item, key) => {
                const accordionButtonEl = item.querySelector(".accordion-button");
                const accordionCollapseEl = item.querySelector(".accordion-collapse");
                if (key !== 0 && accordionCollapseEl.classList.contains("show")) {
                    accordionButtonEl.classList.add("collapsed");
                    accordionButtonEl.setAttribute("aria-expanded", "false");
                    accordionCollapseEl.classList.remove("show");
                }
            });
        },
    };

    setup() {
        const mainEl = this.document.querySelector(ProductPageOption.selector);
        if (mainEl) {
            const productProduct = mainEl.querySelector('[data-oe-model="product.product"]');
            const productTemplate = mainEl.querySelector('[data-oe-model="product.template"]');
            this.productProductID = productProduct ? productProduct.dataset.oeId : null;
            this.productTemplateID = productTemplate ? productTemplate.dataset.oeId : null;
            this.model = "product.template";
            if (this.productProductID) {
                this.model = "product.product";
            }
            // Different targets
            this.productDetailEl = mainEl.querySelector("#product_detail");
            this.productDetailMain = mainEl.querySelector("#product_detail_main");
            this.productPageCarousel = mainEl.querySelector("#o-carousel-product");
            this.productPageGrid = mainEl.querySelector("#o-grid-product");
        }
    }

    forceCarouselRedraw() {
        if (!this.productPageCarousel) {
            return;
        }
        const targetWindow = this.productPageCarousel.ownerDocument.defaultView || window;
        const resizeEvent = new Event('resize');
        targetWindow.dispatchEvent(resizeEvent);
    }
}

// Base class for product page configuration actions
export class BasePreviewableProductPageAction extends PreviewableWebsiteConfigAction {
    static dependencies = [...super.dependencies, "productPageOption"];
    static rpcParameterName = null;
    static shouldForceCarouselRedraw = true;

    async apply({ editingElement, isPreviewing, params, value }) {
        await super.apply({ editingElement, isPreviewing, params, value });

        if (this.constructor.shouldForceCarouselRedraw) {
            this.dependencies.productPageOption.forceCarouselRedraw();
        }
        if (!isPreviewing) {
            await this.makeRpcCall(value);
        }
    }

    async makeRpcCall(value) {
        if (this.constructor.rpcParameterName) {
            await rpc("/shop/config/website", { [this.constructor.rpcParameterName]: value });
        }
    }
}
export class ProductPageContainerWidthAction extends BasePreviewableProductPageAction {
    static id = "productPageContainerWidth";
    static rpcParameterName = "product_page_container";
}

export class ProductPageContainerOrderAction extends BasePreviewableProductPageAction {
    static id = "productPageContainerOrder";
    static rpcParameterName = "product_page_cols_order";
    static shouldForceCarouselRedraw = false;
}

export class ProductPageImageRatioAction extends BasePreviewableProductPageAction {
    static id = "productPageImageRatio";
    static rpcParameterName = "product_page_image_ratio";
}

export class ProductPageImageRatioMobileAction extends BasePreviewableProductPageAction {
    static id = "productPageImageRatioMobile";
    static rpcParameterName = "product_page_image_ratio_mobile";
}

export class ProductPageImageWidthAction extends BasePreviewableProductPageAction {
    static id = "productPageImageWidth";
    static rpcParameterName = "product_page_image_width";
}

export class ProductPageImageGridSpacingAction extends BasePreviewableProductPageAction {
    static id = "productPageImageGridSpacing";
    static rpcParameterName = "product_page_image_spacing";
}

export class ProductPageImageRoundnessAction extends BasePreviewableProductPageAction {
    static id = "productPageRoundness";
    static rpcParameterName = "product_page_image_roundness";
}

export class ProductPageImageLayoutAction extends WebsiteConfigAction {
    static id = "productPageImageLayout";
    static dependencies = [...super.dependencies, "customizeWebsite", "productPageOption"];
    isApplied({ editingElement: productDetailMainEl, value }) {
        return productDetailMainEl.dataset.imageLayout === value;
    }
    getValue({ editingElement: productDetailMainEl }) {
        return productDetailMainEl.dataset.imageLayout;
    }
    async apply({ value }) {
        return rpc("/shop/config/website", { product_page_image_layout: value });
    }
}

export class BaseProductPageAction extends BuilderAction {
    static id = "baseProductPage";
    setup() {
        this.reload = {};
        const mainEl = this.document.querySelector(ProductPageOption.selector);
        if (mainEl) {
            const productProduct = mainEl.querySelector('[data-oe-model="product.product"]');
            const productTemplate = mainEl.querySelector('[data-oe-model="product.template"]');
            this.productProductID = productProduct ? productProduct.dataset.oeId : null;
            this.productTemplateID = productTemplate ? productTemplate.dataset.oeId : null;
            this.model = "product.template";
            if (this.productProductID) {
                this.model = "product.product";
            }
            // Different targets
            this.productDetailMain = mainEl.querySelector("#product_detail_main");
            this.productPageCarousel = mainEl.querySelector("#o-carousel-product");
            this.productPageGrid = mainEl.querySelector("#o-grid-product");
        }
    }
    getSelectedVariantValues(el) {
        const containerEl = el.querySelector(".js_add_cart_variants");
        return wSaleUtils.getSelectedAttributeValues(containerEl);
    }

    async extraMediaSave(el, type, attachments, extraImageEls) {
        if (type === "image") {
            for (const index in attachments) {
                const attachment = attachments[index];
                if (attachment.mimetype.startsWith("image/")) {
                    if (["image/gif", "image/svg+xml"].includes(attachment.mimetype)) {
                        continue;
                    }
                    await this.convertAttachmentToWebp(attachment, extraImageEls[index]);
                }
            }
        }
        await rpc("/shop/product/extra-media", {
            media: attachments,
            type: type,
            product_product_id: this.productProductID,
            product_template_id: this.productTemplateID,
            combination_ids: this.getSelectedVariantValues(el),
        });
    }

    async convertAttachmentToWebp(attachment, imageEl) {
        // This method is widely adapted from onFileUploaded in ImageField.
        // Upon change, make sure to verify whether the same change needs
        // to be applied on both sides.
        if (await isImageCorsProtected(imageEl)) {
            // The image is CORS protected; do not transform it into webp
            return;
        }
        // Generate alternate sizes and format for reports.
        const imgEl = document.createElement("img");
        imgEl.src = imageEl.src;
        await new Promise((resolve) => imgEl.addEventListener("load", resolve));
        const originalSize = Math.max(imgEl.width, imgEl.height);
        const smallerSizes = [1920, 1024, 512, 256, 128].filter((size) => size < originalSize);
        const extension = attachment.name.match(/\.(jpe?|pn)g$/i)?.[0] ?? ".jpeg";
        const webpName = attachment.name.replace(extension, ".webp");
        const format = extension.substr(1).toLowerCase().replace(/^jpg$/, "jpeg");
        const mimetype = `image/${format}`;
        let referenceId = undefined;
        for (const size of [originalSize, ...smallerSizes]) {
            const ratio = size / originalSize;
            const canvas = document.createElement("canvas");
            canvas.width = imgEl.width * ratio;
            canvas.height = imgEl.height * ratio;
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "transparent";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(
                imgEl,
                0,
                0,
                imgEl.width,
                imgEl.height,
                0,
                0,
                canvas.width,
                canvas.height
            );
            const [resizedId] = await this.services.orm.call("ir.attachment", "create_unique", [
                [
                    {
                        name: webpName,
                        description: size === originalSize ? "" : `resize: ${size}`,
                        datas: canvas.toDataURL("image/webp").split(",")[1],
                        res_id: referenceId,
                        res_model: "ir.attachment",
                        mimetype: "image/webp",
                    },
                ],
            ]);
            if (size === originalSize) {
                attachment.original_id = attachment.id;
                attachment.id = resizedId;
                attachment.image_src = `/web/image/${resizedId}-autowebp/${attachment.name}`;
                attachment.mimetype = "image/webp";
            }
            referenceId = referenceId || resizedId; // Keep track of original.
            await this.services.orm.call("ir.attachment", "create_unique", [
                [
                    {
                        name: attachment.name,
                        description: `format: ${format}`,
                        datas: canvas.toDataURL(mimetype).split(",")[1],
                        res_id: resizedId,
                        res_model: "ir.attachment",
                        mimetype: mimetype,
                    },
                ],
            ]);
        }
    }
}

export class ProductPageImageGridColumnsAction extends BaseProductPageAction {
    static id = "productPageImageGridColumns";

    isApplied({ value }) {
        return (parseInt(this.productPageGrid?.dataset.grid_columns) || 1) === value;
    }
    getValue() {
        parseInt(this.productPageGrid?.dataset.grid_columns) || 1;
    }
    async apply({ value }) {
        this.productPageGrid.dataset.grid_columns = value;
        await rpc("/shop/config/website", {
            product_page_grid_columns: value,
        });
    }
}

registry.category("website-plugins").add(ProductPageOptionPlugin.id, ProductPageOptionPlugin);
