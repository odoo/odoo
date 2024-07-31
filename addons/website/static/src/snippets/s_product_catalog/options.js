/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import {
    MultipleItems,
    SnippetOption,
} from "@web_editor/js/editor/snippets.options";
import { updateOption } from "@web_editor/js/editor/snippets.registry";
import {
    registerWebsiteOption,
} from "@website/js/editor/snippets.registry";

export class ProductCatalogOption extends SnippetOption {

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Show/hide descriptions.
     *
     * @see this.selectClass for parameters
     */
    toggleDescription(previewMode, widgetValue, params) {
        const $dishes = this.$('.s_product_catalog_dish');
        if (widgetValue) {
            $dishes.toArray().forEach((el) => {
                const $description = $(el).find('.s_product_catalog_dish_description');
                if ($description.length) {
                    $description.removeClass('d-none');
                } else {
                    const descriptionEl = document.createElement('p');
                    descriptionEl.classList.add('s_product_catalog_dish_description', 'd-block', 'pe-5', 'text-muted', 'o_default_snippet_text');
                    descriptionEl.textContent = _t("Add a description here");
                    el.appendChild(descriptionEl);
                }
            });
        } else {
            $dishes.toArray().forEach((el) => {
                const $description = $(el).find('.s_product_catalog_dish_description');
                if ($description.hasClass('o_default_snippet_text') || $description.find('.o_default_snippet_text').length) {
                    $description.remove();
                } else {
                    $description.addClass('d-none');
                }
            });
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === 'toggleDescription') {
            const $description = this.$('.s_product_catalog_dish_description');
            return $description.length && !$description.hasClass('d-none');
        }
        return super._computeWidgetState(...arguments);
    }
}

registerWebsiteOption("Product Catalog (multiple item add product)", {
    Class: MultipleItems,
    template: "website.s_product_catalog_add_product_option",
    selector: ".s_product_catalog",
    applyTo: "> :has(.s_product_catalog_dish):not(:has(.row > div:has(.s_product_catalog_dish)))",
});
registerWebsiteOption("Product Catalog (multiple item add product in row)", {
    Class: MultipleItems,
    template: "website.s_product_catalog_add_product_option",
    selector: ".s_product_catalog .row > div",
    applyTo: "> :has(.s_product_catalog_dish)",
});
registerWebsiteOption("Product Catalog (Description)", {
    Class: ProductCatalogOption,
    template: "website.s_product_catalog_option",
    selector: ".s_product_catalog",
});
registerWebsiteOption("Product Catalog (Drop)", {
    selector: ".s_product_catalog_dish",
    dropNear: ".s_product_catalog_dish",
});
updateOption("SnippetMove (Vertical)", {
    selector: (SnippetMoveOption) => SnippetMoveOption.selector + ", .s_product_catalog_dish",
});
