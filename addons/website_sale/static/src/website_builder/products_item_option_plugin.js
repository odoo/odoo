import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { BuilderAction } from "@html_builder/core/builder_action";

export class ProductsItemOptionPlugin extends Plugin {
    static id = "productsItemOptionPlugin";
    static shared = ["setProductTemplateID", "getProductTemplateID", "loadInfo"];

    resources = {
        builder_actions: {
            ChangeSequenceAction,
        },
    };

    setup() {
        this.currentWebsiteId = this.services.website.currentWebsiteId;
        this.editMode = false;
    }

    async loadInfo() {
        this.defaultSort = await this.getDefaultSort();
        return this.defaultSort;
    }

    async getDefaultSort() {
        return (
            this.defaultSort ||
            (await this.services.orm.searchRead(
                "website",
                [["id", "=", this.currentWebsiteId]],
                ["shop_default_sort"]
            ))
        );
    }
    setProductTemplateID(value) {
        this.productTemplateID = value;
    }
    getProductTemplateID() {
        return this.productTemplateID;
    }
}

export class ChangeSequenceAction extends BuilderAction {
    static id = "changeSequence";
    static dependencies = ["productsItemOptionPlugin"];
    setup() {
        this.productItemPlugin = this.dependencies.productsItemOptionPlugin;
        this.reload = {};
    }
    apply({ editingElement, value }) {
        this.productItemPlugin.setProductTemplateID(
            parseInt(
                editingElement
                    .querySelector('[data-oe-model="product.template"]')
                    .getAttribute("data-oe-id")
            )
        );
        return rpc("/shop/config/product", {
            product_id: this.productItemPlugin.getProductTemplateID(),
            sequence: value,
        });
    }
}

registry.category("website-plugins").add(ProductsItemOptionPlugin.id, ProductsItemOptionPlugin);
