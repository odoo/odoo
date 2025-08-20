import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { ProductPageOption } from "./product_page_option";
import { rpc } from "@web/core/network/rpc";
import { isImageCorsProtected } from "@html_editor/utils/image";
import { TABS } from "@html_editor/main/media/media_dialog/media_dialog";
import { WebsiteConfigAction } from "@website/builder/plugins/customize_website_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

export const productPageSelector = "main:has(.o_wsale_product_page)";
class ProductPageOptionPlugin extends Plugin {
    static id = "productPageOption";
    static dependencies = ["builderActions", "media", "customizeWebsite"];
    static shared = ["getDisabledOtherZoomViews"];
    resources = {
        builder_options: {
            OptionComponent: ProductPageOption,
            props: {
                getZoomLevels: this.getZoomLevels.bind(this),
            },
            selector: productPageSelector,
            editableOnly: false,
            title: _t("Product Page"),
        },
        builder_actions: {
            ProductPageImageWidthAction,
            ProductPageImageLayoutAction,
            ProductPageImageGridSpacingAction,
            ProductPageImageGridColumnsAction,
            ProductReplaceMainImageAction,
            ProductAddExtraImageAction,
            ProductRemoveAllExtraImagesAction,
        },
        clean_for_save_handlers: ({ root: el }) => {
            const mainEl = el.querySelector(productPageSelector);
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
        const mainEl = this.document.querySelector(productPageSelector);
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
    
    getZoomLevels() {
        const hasImages = this.productDetailMain.dataset.image_width != "none";
        const isFullImage = this.productDetailMain.dataset.image_width == "100_pc";
        return [
            {
                id: "o_wsale_zoom_hover",
                views: ["website_sale.product_picture_magnify_hover"],
                label: _t("Magnifier on hover"),
                visible: hasImages && !isFullImage,
            },
            {
                id: "o_wsale_zoom_click",
                views: ["website_sale.product_picture_magnify_click"],
                label: _t("Pop-up on Click"),
                visible: hasImages,
            },
            {
                id: "o_wsale_zoom_both",
                views: ["website_sale.product_picture_magnify_both"],
                label: _t("Both"),
                visible: hasImages && !isFullImage,
            },
            {
                id: "o_wsale_zoom_none",
                views: [],
                label: _t("None"),
                visible: hasImages,
            },
        ];
    }
    getZoomViews() {
        const views = [];
        for (const zoomLevel of this.getZoomLevels()) {
            views.push(...zoomLevel.views);
        }
        return views;
    }
    getDisabledOtherZoomViews(keptView) {
        return this.getZoomViews().map((view) => (view === keptView ? view : `!${view}`));
    }
}

export class ProductPageImageWidthAction extends WebsiteConfigAction {
    static id = "productPageImageWidth";
    static dependencies = ["customizeWebsite", "productPageOption"];
    isApplied({ editingElement: productDetailMainEl, value }) {
        return productDetailMainEl.dataset.image_width === value;
    }
    getValue({ editingElement: productDetailMainEl }) {
        return productDetailMainEl.dataset.image_width;
    }
    async apply({ value }) {
        if (value === "100_pc") {
            const defaultZoomOption = "website_sale.product_picture_magnify_click";
            await super.apply({
                params: {
                    views: this.dependencies.productPageOption.getDisabledOtherZoomViews(defaultZoomOption),
                },
            });
        }
        await rpc("/shop/config/website", { product_page_image_width: value });
    }
}
export class ProductPageImageLayoutAction extends WebsiteConfigAction {
    static id = "productPageImageLayout";
    static dependencies = ["customizeWebsite", "productPageOption"];
    isApplied({ editingElement: productDetailMainEl, value }) {
        return productDetailMainEl.dataset.image_layout === value;
    }
    getValue({ editingElement: productDetailMainEl }) {
        return productDetailMainEl.dataset.image_layout;
    }
    async apply({ editingElement: productDetailMainEl, value }) {
        const imageWidthOption = productDetailMainEl.dataset.image_width;
        let defaultZoomOption =
            value === "grid"
                ? "website_sale.product_picture_magnify_click"
                : "website_sale.product_picture_magnify_hover";
        if (
            imageWidthOption === "100_pc" &&
            defaultZoomOption === "website_sale.product_picture_magnify_hover"
        ) {
            defaultZoomOption = "website_sale.product_picture_magnify_click";
        }
        await super.apply({
            params: {
                views: this.dependencies.productPageOption.getDisabledOtherZoomViews(defaultZoomOption),
            },
        });
        return rpc("/shop/config/website", { product_page_image_layout: value });
    }
}

export class BaseProductPageAction extends BuilderAction {
    static id = "baseProductPage";
    setup() {
        this.reload = {};
        const mainEl = this.document.querySelector(productPageSelector);
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
        const fullCombinationEl = containerEl.querySelector(
            "input.js_product_change:checked[data-combination]"
        );
        if (fullCombinationEl) {
            return fullCombinationEl.dataset.combination;
        }
        const values = [];
        const variantsValuesSelectors = [
            "input.js_variant_change:checked",
            "select.js_variant_change",
        ];
        for (const fieldEl of containerEl.querySelectorAll(variantsValuesSelectors.join(", "))) {
            values.push(parseInt(fieldEl.value) || 0);
        }
        return values;
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
        const smallerSizes = [1024, 512, 256, 128].filter((size) => size < originalSize);
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
                        datas: canvas.toDataURL("image/webp", 0.75).split(",")[1],
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
                        datas: canvas.toDataURL(mimetype, 0.75).split(",")[1],
                        res_id: resizedId,
                        res_model: "ir.attachment",
                        mimetype: mimetype,
                    },
                ],
            ]);
        }
    }
}
export class ProductPageImageGridSpacingAction extends BaseProductPageAction {
    static id = "productPageImageGridSpacing";
    getValue() {
        if (!this.productPageGrid) {
            return 0;
        }
        return {
            none: 0,
            small: 1,
            medium: 2,
            big: 3,
        }[this.productPageGrid.dataset.image_spacing];
    }
    async load({ value }) {
        const spacing = {
            0: "none",
            1: "small",
            2: "medium",
            3: "big",
        }[value];

        await rpc("/shop/config/website", {
            product_page_image_spacing: spacing,
        });
        return spacing;
    }
    apply({ loadResult: spacing }) {
        this.productPageGrid.dataset.image_spacing = spacing;
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
export class ProductReplaceMainImageAction extends BaseProductPageAction {
    static id = "productReplaceMainImage";
    static dependencies = ["media_website"];
    setup() {
        super.setup();
        this.reload = false;
    }
    apply({ editingElement: productDetailMainEl }) {
        // Emulate click on the main image of the carousel.
        const image = productDetailMainEl.querySelector(
            `[data-oe-model="${this.model}"][data-oe-field=image_1920] img`
        );
        this.dependencies.media_website.replaceMedia(image);
    }
}

export class ProductAddExtraImageAction extends BaseProductPageAction {
    static id = "productAddExtraImage";
    static dependencies = ["media"];
    async apply({ editingElement: el }) {
        // Prompts the user for images, then saves the new images.
        if (this.model === "product.template") {
            this.services.notification.add(
                'Pictures will be added to the main image. Use "Instant" attributes to set pictures on each variants',
                { type: "info" }
            );
        }
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                addFieldImage: true,
                multiImages: true,
                noDocuments: true,
                noIcons: true,
                node: el,
                // Kinda hack-ish but the regular save does not get the information we need
                save: async (imgEls, selectedMedia, activeTab) => {
                    if (selectedMedia.length) {
                        const type =
                            activeTab === TABS["IMAGES"].id ? "image" : "video";
                        await this.extraMediaSave(el, type, selectedMedia, imgEls);
                    }
                },
            });
            onClose.then(resolve);
        });
    }
}
export class ProductRemoveAllExtraImagesAction extends BaseProductPageAction {
    static id = "productRemoveAllExtraImages";
    async apply({ editingElement: el }) {
        // Removes all extra-images from the product.
        await rpc(`/shop/product/clear-images`, {
            model: this.model,
            product_product_id: this.productProductID,
            product_template_id: this.productTemplateID,
            combination_ids: this.getSelectedVariantValues(el),
        })
    }
}

registry.category("website-plugins").add(ProductPageOptionPlugin.id, ProductPageOptionPlugin);
