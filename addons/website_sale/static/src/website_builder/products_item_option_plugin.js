import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { ProductsItemOption } from "./products_item_option";
import { reactive } from "@odoo/owl";
import { BuilderAction } from "@html_builder/core/builder_action";

class ProductsItemOptionPlugin extends Plugin {
    static id = "productsItemOptionPlugin";
    static shared = [
        "setItemSize",
        "setProductTemplateID",
        "getProductTemplateID",
    ];
    itemSize = reactive({ x: 1, y: 1 });

    resources = {
        builder_options: [
            {
                OptionComponent: ProductsItemOption,
                props: {
                    loadInfo: this.loadInfo.bind(this),
                    itemSize: this.itemSize,
                },
                selector: "#products_grid .oe_product",
                editableOnly: false,
                title: _t("Product"),
                groups: ["website.group_website_designer"],
            },
        ],

        builder_actions: {
            SetItemSizeAction,
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
    setItemSize(x, y) {
        this.itemSize.x = x;
        this.itemSize.y = y;
    }
    setProductTemplateID(value) {
        this.productTemplateID = value;
    }
    getProductTemplateID() {
        return this.productTemplateID;
    }
}

export class SetItemSizeAction extends BuilderAction {
    static id = "setItemSize";
    static dependencies = ["productsItemOptionPlugin"];
    setup() {
        this.productItemPlugin = this.dependencies.productsItemOptionPlugin;
        this.reload = {};
    }
    isApplied({ editingElement, value: [i, j] }) {
        if (
            parseInt(editingElement.dataset.rowspan || 1) - 1 === i &&
            parseInt(editingElement.dataset.colspan || 1) - 1 === j
        ) {
            this.productItemPlugin.setItemSize(j + 1, i + 1);
            return true;
        }
        return false;
    }
    apply({ editingElement, value: [i, j] }) {
        const x = j + 1;
        const y = i + 1;

        this.productItemPlugin.setProductTemplateID(
            parseInt(
                editingElement
                    .querySelector('[data-oe-model="product.template"]')
                    .getAttribute("data-oe-id")
            )
        );
        return rpc("/shop/config/product", {
            product_id: this.productItemPlugin.getProductTemplateID(),
            x: x,
            y: y,
        });
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
