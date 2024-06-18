/** @odoo-module **/

import { DynamicSnippetCarouselOptions } from "@website/snippets/s_dynamic_snippet_carousel/options";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

const alternativeSnippetRemovedOptions = [
    'filter_opt', 'product_category_opt', 'product_tag_opt', 'product_names_opt',
]

export class DynamicSnippetProductsOptions extends DynamicSnippetCarouselOptions {

    /**
     * @override
     */
    async willStart() {
        this.productCategories = await this._fetchProductCategories();
        this.modelNameFilter = 'product.product';
        const productTemplateId = this.$target.closest("#wrapwrap").find("input.product_template_id");
        this.hasProductTemplateId = productTemplateId.val();
        if (!this.hasProductTemplateId) {
            this.contextualFilterDomain.push(['product_cross_selling', '=', false]);
        }
        this.isAlternativeProductSnippet = this.$target.hasClass('o_wsale_alternative_products');
        await super.willStart();
        this.renderContext.productCategories = this.productCategories;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override
     */
     _computeWidgetVisibility(widgetName, params) {
        if (this.isAlternativeProductSnippet && alternativeSnippetRemovedOptions.includes(widgetName)) {
            return false;
        }
        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * Fetches product categories.
     * @private
     * @returns {Promise}
     */
    _fetchProductCategories() {
        const websiteId = this.env.services.website.currentWebsite.id;
        const websiteDomain = ["|", ["website_id", "=", false], ["website_id", "=", websiteId]];
        return this.env.services.orm.searchRead("product.public.category", websiteDomain, ["id", "name"]);
    }
    /**
     * Renders the product categories option selector content into the provided uiFragment.
     * @private
     * @param {HTMLElement} uiFragment
     */
    async _getRenderContext() {
        const renderContext = super._getRenderContext();
        renderContext.productCategories = this.productCategories;
        return renderContext;
    }
    /**
     * @override
     * @private
     */
    _setOptionsDefaultValues() {
        this._setOptionValue('productCategoryId', 'all');
        this._setOptionValue('showVariants', true);
        super._setOptionsDefaultValues(...arguments);
    }
}

registerWebsiteOption("DynamicSnippetProductsOptions", {
    Class: DynamicSnippetProductsOptions,
    template: "website_sale.s_dynamic_snippet_products_template_option",
    selector: ".s_dynamic_snippet_products",
});
