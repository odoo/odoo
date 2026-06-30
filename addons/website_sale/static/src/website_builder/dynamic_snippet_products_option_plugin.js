import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { getContextualFilterDomain } from "./dynamic_snippet_products_option";

export class DynamicSnippetProductsOptionPlugin extends Plugin {
    static id = "dynamicSnippetProductsOption";
    static shared = ["fetchCategories"];
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        dynamic_filter_search_domain_processors: (
            domain,
            { productRibbonIds, productTagIds, productNames, productCategoryId }
        ) => {
            if (productRibbonIds?.length) {
                const ribbonIds = productRibbonIds.map((productRibbon) => productRibbon.id);
                domain.push(
                    "|",
                    ["variant_ribbon_id", "in", ribbonIds],
                    "&",
                    ["variant_ribbon_id", "=", false],
                    ["product_tmpl_id.website_ribbon_id", "in", ribbonIds]
                );
            }
            if (productTagIds?.length) {
                domain.push(["all_product_tag_ids", "in", productTagIds.map((e) => e.id)]);
            }
            if (productNames) {
                const nameDomain = [];
                for (const productName of productNames.split(",")) {
                    // Ignore empty names
                    if (!productName.length) {
                        continue;
                    }
                    // Search on name, internal reference and barcode.
                    if (nameDomain.length) {
                        nameDomain.unshift("|");
                    }
                    nameDomain.push(
                        ...[
                            "|",
                            "|",
                            ["name", "ilike", productName],
                            ["default_code", "=", productName],
                            ["barcode", "=", productName],
                        ]
                    );
                }
                domain.push(...nameDomain);
            }
            if (productCategoryId) {
                domain.push(["public_categ_ids", "child_of", productCategoryId]);
            }
            return domain;
        },
        dynamic_filter_contextual_domain_processors: (domain, { snippetEl }) => {
            if (snippetEl.matches(".s_dynamic_snippet_products")) {
                domain.push(...getContextualFilterDomain(this.editable));
            }
            return domain;
        },
        model_name_filter_overrides: (snippetEl) => {
            if (snippetEl.matches(".s_dynamic_snippet_products")) {
                return "product.product";
            }
        },
    };
    setup() {
        this.categories = undefined;
    }
    destroy() {
        super.destroy();
        this.categories = undefined;
    }
    async fetchCategories() {
        if (!this.categories) {
            this.categories = this._fetchCategories();
        }
        return this.categories;
    }
    async _fetchCategories() {
        // TODO put in an utility function
        const websiteDomain = [
            "|",
            ["website_id", "=", false],
            ["website_id", "=", this.services.website.currentWebsite.id],
        ];
        return this.services.orm.searchRead(
            "product.public.category",
            websiteDomain,
            ["id", "name"],
            { order: "name asc" }
        );
    }
}

registry
    .category("website-plugins")
    .add(DynamicSnippetProductsOptionPlugin.id, DynamicSnippetProductsOptionPlugin);
