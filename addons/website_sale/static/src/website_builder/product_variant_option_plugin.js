import { SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { TABS } from "@html_editor/main/media/media_dialog/media_dialog";
import { registry } from "@web/core/registry";
import { ProductVariantOption } from "./product_variant_option";
import { BaseProductPageAction } from "./product_page_option_plugin";

export class ProductVariantOptionPlugin extends Plugin {
    static id = "productVariantOptionPlugin";
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC_END, ProductVariantOption),
        ],
        builder_actions: {
            ProductAddImageAction,
        },
        container_title: {
            selector: ProductVariantOption.selector,
            getTitleExtraInfo: (el) => {
                const titleEl = el.querySelector(".o_wsale_product_details_content_section_title")?.querySelector("h1");
                return titleEl ? titleEl.dataset.variantName : "";
            },
            editableOnly: false,
        },
        patch_builder_options: [
            {
                target_name: 'ProductVariantRibbonOption',
                target_element: 'selector',
                method: 'replace',
                value: ProductVariantOption.selector,
            },
        ],
    };
}

export class ProductAddImageAction extends BaseProductPageAction {
    static id = "productAddImage";
    static dependencies = [...super.dependencies, "media"];
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
                visibleTabs: ["IMAGES", "VIDEOS"],
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

registry.category("website-plugins")
        .add(ProductVariantOptionPlugin.id, ProductVariantOptionPlugin);
