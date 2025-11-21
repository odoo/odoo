import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class ProductTagOption extends BaseOptionComponent {
    static template = "website_sale.ProductTagOption";
    static selector = "#product_detail .o_wsale_product_tag";
    static title = _t("Tag");
    static editableOnly = false;
    static reloadTarget = true;
}

class ProductTagOptionPlugin extends Plugin {
    static id = "productTagOption";
    resources = {
        builder_options: ProductTagOption,
        builder_actions: {
            ProductTagColorAction,
            ProductTagImageAction,
        },
    };

}

export class ProductTagColorAction extends BuilderAction {
    static id = "productTagColorAction";
    static dependencies = ["savePlugin"];

    setup() {
        this.reload = true;
    }

    getValue({ editingElement: el }) {
        return el.style.color;
    }

    async apply({ editingElement: el, value }) {
        const tag_id = parseInt(
            el.dataset.oeId
        );
        await rpc("/shop/config/tag", {
            tag_id: tag_id,
            color: value,
        });
        await this.dependencies.savePlugin.save();
        await this.config.reloadEditor();
    }
}

export class ProductTagImageAction extends BuilderAction {
    static id = "productTagImageAction";
    static dependencies = ["media"];

    setup() {
        this.reload = true;
    }

    async apply({ editingElement: el }) {
        const tag_id = parseInt(
            el.dataset.oeId
        );
        // Choose an image with the media dialog.
        let imageEl, attachment_id;
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                onlyImages: true,
                noDocuments: true,
                save: (selectedImageEl, selectedMedia) => {
                    imageEl = selectedImageEl;
                    attachment_id = selectedMedia[0]['id'];
                },
            });
            onClose.then(resolve);
        });
        if (!imageEl) {
            return;
        }

        await rpc("/shop/config/tag", {
            tag_id: tag_id,
            image: attachment_id,
        });
    }
}

registry
    .category("website-plugins")
    .add(ProductTagOptionPlugin.id, ProductTagOptionPlugin);
