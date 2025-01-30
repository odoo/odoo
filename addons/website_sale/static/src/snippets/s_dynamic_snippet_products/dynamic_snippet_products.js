import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { registry } from "@web/core/registry";

export class DynamicSnippetProducts extends DynamicSnippetCarousel {
    static selector = ".s_dynamic_snippet_products";

    /**
     * Gets the category search domain
     */
    getCategorySearchDomain() {
        const searchDomain = [];
        let productCategoryId = this.el.dataset.productCategoryId;
        if (productCategoryId && productCategoryId !== "all") {
            if (productCategoryId === "current") {
                productCategoryId = undefined;
                const productCategoryFieldEl = this.el.closest("body").querySelector("#product_details .product_category_id");
                if (productCategoryFieldEl) {
                    productCategoryId = parseInt(productCategoryFieldEl.value);
                }
                if (!productCategoryId) {
                    const mainObject = this.services.website_page.mainObject;
                    if (mainObject.model === "product.public.category") {
                        productCategoryId = mainObject.id;
                    }
                }
                if (!productCategoryId) {
                    // Try with categories from product, unfortunately the category hierarchy is not matched with this approach
                    const productTemplateIdEl = this.el.closest("body").querySelector("#product_details .product_category_id");
                    if (productTemplateIdEl) {
                        searchDomain.push(["public_categ_ids.product_tmpl_ids", "=", parseInt(productTemplateIdEl.value)]);
                    }
                }
            }
            if (productCategoryId) {
                searchDomain.push(["public_categ_ids", "child_of", parseInt(productCategoryId)]);
            }
        }
        return searchDomain;
    }

    getTagSearchDomain() {
        const searchDomain = [];
        let productTagIds = this.el.dataset.productTagIds;
        productTagIds = productTagIds ? JSON.parse(productTagIds) : [];
        if (productTagIds.length) {
            searchDomain.push(["all_product_tag_ids", "in", productTagIds.map(productTag => productTag.id)]);
        }
        return searchDomain;
    }

    /**
     * @override
     */
    getSearchDomain() {
        const searchDomain = super.getSearchDomain(...arguments);
        searchDomain.push(...this.getCategorySearchDomain());
        searchDomain.push(...this.getTagSearchDomain());
        const productNames = this.el.dataset.productNames;
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
                nameDomain.push(...[
                    "|", "|", ["name", "ilike", productName],
                    ["default_code", "=", productName],
                    ["barcode", "=", productName],
                ]);
            }
            searchDomain.push(...nameDomain);
        }
        if (!this.el.dataset.showVariants) {
            searchDomain.push("hide_variants");
        }
        return searchDomain;
    }

    /**
     * @override
     */
    getRpcParameters() {
        const productTemplateIdEl = document.body.querySelector("#product_details .product_template_id");
        return Object.assign(super.getRpcParameters(...arguments), {
            productTemplateId: productTemplateIdEl ? productTemplateIdEl.value : undefined,
        });
    }
}

registry
    .category("public.interactions")
    .add("website_sale.dynamic_snippet_products", DynamicSnippetProducts);

registry
    .category("public.interactions.edit")
    .add("website_sale.dynamic_snippet_products", {
        Interaction: DynamicSnippetProducts,
    });
