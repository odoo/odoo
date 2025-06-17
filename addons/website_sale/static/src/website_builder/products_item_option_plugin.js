import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { ProductsItemOption } from "./products_item_option";
import { reactive } from "@odoo/owl";

class ProductsItemOptionPlugin extends Plugin {
    static id = "productsItemOptionPlugin";
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

        builder_actions: this.getActions(),
    };

    setup() {
        this.currentWebsiteId = this.services.website.currentWebsiteId;
        this.editMode = false;
    }

    getActions() {
        return {
            setItemSize: {
                reload: {},
                isApplied: ({ editingElement, value: [i, j] }) => {
                    if (
                        parseInt(editingElement.dataset.rowspan || 1) - 1 === i &&
                        parseInt(editingElement.dataset.colspan || 1) - 1 === j
                    ) {
                        this.itemSize.x = j + 1;
                        this.itemSize.y = i + 1;
                        return true;
                    }
                    return false;
                },

                apply: ({ editingElement, value: [i, j] }) => {
                    const x = j + 1;
                    const y = i + 1;

                    this.productTemplateID = parseInt(
                        editingElement
                            .querySelector('[data-oe-model="product.template"]')
                            .getAttribute("data-oe-id")
                    );
                    return rpc("/shop/config/product", {
                        product_id: this.productTemplateID,
                        x: x,
                        y: y,
                    });
                },
            },
            changeSequence: {
                reload: {},
                apply: ({ editingElement, value }) => {
                    this.productTemplateID = parseInt(
                        editingElement
                            .querySelector('[data-oe-model="product.template"]')
                            .getAttribute("data-oe-id")
                    );
                    return rpc("/shop/config/product", {
                        product_id: this.productTemplateID,
                        sequence: value,
                    });
                },
            },
        };
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
}

registry.category("website-plugins").add(ProductsItemOptionPlugin.id, ProductsItemOptionPlugin);
