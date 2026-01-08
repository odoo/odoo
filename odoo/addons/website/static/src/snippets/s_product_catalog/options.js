/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import options from "@web_editor/js/editor/snippets.options";

options.registry.ProductCatalog = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Show/hide descriptions.
     *
     * @see this.selectClass for parameters
     */
    toggleDescription: function (previewMode, widgetValue, params) {
        const $dishes = this.$('.s_product_catalog_dish');
        const $name = $dishes.find('.s_product_catalog_dish_name');
        $name.toggleClass('s_product_catalog_dish_dot_leaders', !widgetValue);
        if (widgetValue) {
            $dishes.toArray().forEach((el) => {
                const $description = $(el).find('.s_product_catalog_dish_description');
                if ($description.length) {
                    $description.removeClass('d-none');
                } else {
                    const descriptionEl = document.createElement('p');
                    descriptionEl.classList.add('s_product_catalog_dish_description', 'border-top', 'text-muted', 'pt-1', 'o_default_snippet_text');
                    const iEl = document.createElement('i');
                    iEl.textContent = _t("Add a description here");
                    descriptionEl.appendChild(iEl);
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
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        if (methodName === 'toggleDescription') {
            const $description = this.$('.s_product_catalog_dish_description');
            return $description.length && !$description.hasClass('d-none');
        }
        return this._super(...arguments);
    },
});
