import { ProductsListPageOption } from "@website_sale/website_builder/products_list_page_option";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { BuilderAction } from "@html_builder/core/builder_action";

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
        builder_actions: {
            SetPpgAction,
            SetPprAction,
            SetGapAction,
            SetDefaultSortAction,
        },
        save_handlers: this.onSave.bind(this),
    };

    async onSave() {
        const pageEl = this.editable.querySelector("#o_wsale_container");
        if (pageEl) {
            const updateData = {};

            const gapToSave = pageEl.dataset.gapToSave;
            if (typeof gapToSave !== "undefined") {
                updateData.shop_gap = gapToSave;
            }

            // Define class groups to save in fields
            const classGroups = [
                {
                    prefix: 'o_wsale_design_',
                    field: 'shop_opt_products_design_class'
                },
                {
                    prefix: 'o_wsale_products_opt_hover_',
                    field: 'shop_opt_products_hover_effect_class'
                },
                {
                    prefix: 'o_wsale_products_opt_text_align_',
                    field: 'shop_opt_products_text_align_class'
                },
                {
                    prefix: 'o_wsale_products_opt_name_color_',
                    field: 'shop_opt_products_name_color_class'
                },
                {
                    prefix: 'o_wsale_products_opt_img_secondary_',
                    field: 'shop_opt_products_img_secondary_class'
                },
                {
                    prefix: 'o_wsale_products_opt_img_hover_',
                    field: 'shop_opt_products_img_hover_class'
                },
            ];

            // Process each class group and add to update data
            for (const group of classGroups) {
                const classes = this.extractClassesByPrefix(pageEl, group.prefix);
                if (classes !== null) {
                    updateData[group.field] = classes;
                }
            }

            // Single RPC call
            if (Object.keys(updateData).length > 0) {
                console.log("Attempt rpc call:")
                console.log(updateData)
                console.log("////")
                return rpc("/shop/config/website", updateData);
            }
        }
    }

    /**
    * Extract classes that start with a specific prefix from an element
    * @param {Element} element - The DOM element to scan
    * @param {string} prefix - The class prefix to look for (e.g., 'o_wsale_products_opt_hover_')
    * @returns {string} Matching classes, or empty string if none found
    */
    extractClassesByPrefix(element, prefixes) {
        // Normalize prefixes to array
        const prefixArray = Array.isArray(prefixes) ? prefixes : [prefixes];

        const classList = Array.from(element.classList);
        const matchingClasses = [];

        // Find all classes that start with any of the specified prefixes
        for (const className of classList) {
            for (const prefix of prefixArray) {
                if (className.startsWith(prefix)) {
                    matchingClasses.push(className);
                    break; // Don't check other prefixes for this class
                }
            }
        }

        matchingClasses.sort();

        return matchingClasses.join(' ');
    }
}

class SetPpgAction extends BuilderAction {
    static id = "setPpg";
    setup() {
        this.reload = {};
    }
    getValue({ editingElement }) {
        return parseInt(editingElement.dataset.ppg);
    }
    apply({ value }) {
        const PPG_LIMIT = 10000;
        let ppg = parseInt(value);
        if (!ppg || ppg < 1) {
            return false;
        }
        ppg = Math.min(ppg, PPG_LIMIT);
        return rpc("/shop/config/website", { shop_ppg: ppg });
    }
}
class SetPprAction extends BuilderAction {
    static id = "setPpr";
    setup() {
        this.reload = {};
    }
    isApplied({ editingElement, value }) {
        return parseInt(editingElement.dataset.ppr) === value;
    }
    apply({ value }) {
        const ppr = parseInt(value);
        return rpc("/shop/config/website", { shop_ppr: ppr });
    }
}
class SetGapAction extends BuilderAction {
    static id = "setGap";
    setup() {
        this.reload = {};
    }
    isApplied() {
        return true;
    }
    getValue({ editingElement }) {
        return editingElement.style.getPropertyValue("--o-wsale-products-grid-gap");
    }
    apply({ editingElement, value }) {
        editingElement.style.setProperty("--o-wsale-products-grid-gap", value);
        editingElement.dataset.gapToSave = value;
    }
}
class SetDefaultSortAction extends BuilderAction {
    static id = "setDefaultSort";
    setup() {
        this.reload = {};
    }
    isApplied({ editingElement, value }) {
        return editingElement.dataset.defaultSort === value;
    }
    apply({ value }) {
        return rpc("/shop/config/website", { shop_default_sort: value });
    }
}

registry
    .category("website-plugins")
    .add(ProductsListPageOptionPlugin.id, ProductsListPageOptionPlugin);
