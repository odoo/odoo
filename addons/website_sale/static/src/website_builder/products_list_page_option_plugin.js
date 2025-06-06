import { ProductsListPageOption } from "@website_sale/website_builder/products_list_page_option";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

class ProductsListPageOptionPlugin extends Plugin {
    static id = "productsListPageOptionPlugin";

    resources = {
        builder_options: [
            {
                OptionComponent: ProductsListPageOption,
                selector: "main:has(.o_wsale_products_page)",
                applyTo: "#o_wsale_container",
                editableOnly: false,
                title: _t("Products Page"),
                groups: ["website.group_website_designer"],
            },
        ],
        builder_actions: this.getActions(),
    };

    getActions() {
        return {
            setPpg: {
                reload: {},
                getValue: ({ editingElement }) => parseInt(editingElement.dataset.ppg),
                apply: ({ value }) => {
                    const PPG_LIMIT = 10000;
                    let ppg = parseInt(value);
                    if (!ppg || ppg < 1) {
                        return false;
                    }
                    ppg = Math.min(ppg, PPG_LIMIT);
                    return rpc("/shop/config/website", { shop_ppg: ppg });
                },
            },
            setPpr: {
                reload: {},
                isApplied: ({ editingElement, value }) =>
                    parseInt(editingElement.dataset.ppr) === value,
                apply: ({ value }) => {
                    const ppr = parseInt(value);
                    return rpc("/shop/config/website", { shop_ppr: ppr });
                },
            },
            setGap: {
                reload: {},
                apply: ({ value }) => rpc("/shop/config/website", { shop_gap: value }),
            },
            setDefaultGap: {
                reload: {},
                apply: ({ editingElement, value }) => {
                    editingElement.style.setProperty("--o-wsale-products-grid-gap", value + "px");
                    return rpc("/shop/config/website", { shop_gap: value });
                },
            },
            setDefaultSort: {
                reload: {},
                isApplied: ({ editingElement, value }) =>
                    editingElement.dataset.defaultSort === value,
                apply: ({ value }) => rpc("/shop/config/website", { shop_default_sort: value }),
            },
        };
    }
}

registry
    .category("website-plugins")
    .add(ProductsListPageOptionPlugin.id, ProductsListPageOptionPlugin);
