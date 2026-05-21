import { DynamicSnippetCarousel } from "@website/snippets/s_dynamic_snippet_carousel/dynamic_snippet_carousel";
import { registry } from "@web/core/registry";

export class DynamicSnippetProducts extends DynamicSnippetCarousel {
    static selector = ".s_dynamic_snippet_products";

    async willStart() {
        const superWillStart = super.willStart();
        const mainObject = this.services.website_page.mainObject;
        if (
            this.el.dataset.productCategoryId === "current" &&
            mainObject.model === "product.template"
        ) {
            const readResult = await this.services.orm.read(
                mainObject.model,
                [mainObject.id],
                ["public_categ_ids"]
            );
            this.categoryOfCurrentProduct = readResult[0]?.public_categ_ids[0];
        }
        return superWillStart;
    }

    /**
     * Gets the category search domain
     */
    getCategorySearchDomain() {
        const searchDomain = [];
        let productCategoryId = this.el.dataset.productCategoryId;
        if (productCategoryId && productCategoryId !== "all") {
            if (productCategoryId === "current") {
                productCategoryId = this.categoryOfCurrentProduct;
                const mainObject = this.services.website_page.mainObject;
                if (!productCategoryId) {
                    if (mainObject.model === "product.public.category") {
                        productCategoryId = mainObject.id;
                    }
                }
                if (!productCategoryId) {
                    // Try with categories from product, unfortunately the category hierarchy is not matched with this approach
                    if (mainObject.model === "product.template") {
                        searchDomain.push(["public_categ_ids.product_tmpl_ids", "=", mainObject.id]);
                    }
                }
            }
            if (productCategoryId) {
                searchDomain.push(["public_categ_ids", "child_of", parseInt(productCategoryId)]);
            }
        }
        return searchDomain;
    }

    getRibbonSearchDomain() {
        const productRibbonIds = JSON.parse(this.el.dataset.productRibbonIds || '[]');
        if (!productRibbonIds.length) {
            return [];
        }
        const ribbonIds = productRibbonIds.map(productRibbon => productRibbon.id);

        return [
            '|',
                ['variant_ribbon_id', 'in', ribbonIds],
                '&',
                    ['variant_ribbon_id', '=', false],
                    ['product_tmpl_id.website_ribbon_id', 'in', ribbonIds],
        ];
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
        searchDomain.push(...this.getRibbonSearchDomain());
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
        const mainObject = this.services.website_page.mainObject;
        return Object.assign(super.getRpcParameters(...arguments), {
            productTemplateId: mainObject.model === "product.template" ? mainObject.id : undefined,
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

registry
    .category("public.interactions.preview")
    .add("website_sale.dynamic_snippet_products", {
        Interaction: DynamicSnippetProducts,
    });
