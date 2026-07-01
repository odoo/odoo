import { Plugin } from "@html_editor/plugin";
import { TABS } from "@html_editor/main/media/media_dialog/media_dialog_utils";
import { registry } from "@web/core/registry";
import { BaseProductPageAction } from "./product_page_option_plugin";
import { BuilderAction } from "@html_builder/core/builder_action";

export class ProductVariantOptionPlugin extends Plugin {
    static id = "productVariantOptionPlugin";
    resources = {
        builder_actions: {
            ProductAddImageAction,
        },
        builder_options_render_context: {
            productVariantOptionSelector: "#product_detail",
        },
    };
}

export class ProductAddImageAction extends BaseProductPageAction {
    static id = "productAddImage";
    static dependencies = [...super.dependencies, "media"];
    setup() {
        super.setup();
        this.canTimeout = false;
    }
    async load({ editingElement: el }) {
        return new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog(
                this.getMediaDialogProps({
                    editingElement: el,
                    loadPromiseResolveFunction: resolve,
                })
            );
            // Make sure to resolve with a Falsy value when the mediaDialog is closed without selecting an image so that
            // loadResult is Falsy and apply() cancels the reload of the page.
            onClose.then(() => resolve());
        });
    }

    getMediaDialogProps({ editingElement, loadPromiseResolveFunction }) {
        return {
            addFieldImage: true,
            multiImages: true,
            visibleTabs: ["IMAGES", "VIDEOS"],
            node: editingElement,
            // Kinda hack-ish but the regular save does not get the information we need
            save: async (imgEls, selectedMedia, activeTab) => {
                if (selectedMedia.length) {
                    const type = activeTab === TABS["IMAGES"].id ? "image" : "video";
                    loadPromiseResolveFunction({ imgEls, selectedMedia, type });
                }
            },
        };
    }
    async apply({ editingElement: el, loadResult }) {
        if (!loadResult) {
            return BuilderAction.cancelReload;
        }
        const { imgEls, selectedMedia, type } = loadResult;
        await this.extraMediaSave(el, type, selectedMedia, imgEls);
    }
}

registry.category("website-plugins").add(ProductVariantOptionPlugin.id, ProductVariantOptionPlugin);
