
odoo.define('website.s_product_catalog_options', function (require) {
'use strict';

const core = require('web.core');
const options = require('web_editor.snippets.options');

const _t = core._t;

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
        if (widgetValue) {
            _.each($dishes, el => {
                const $description = $(el).find('.s_product_catalog_dish_description');
                if ($description.length) {
                    $description.removeClass('d-none');
                } else {
                    const descriptionEl = document.createElement('p');
                    descriptionEl.classList.add('s_product_catalog_dish_description', 'o_default_snippet_text');
                    descriptionEl.textContent = _t("Add a description here");
                    el.appendChild(descriptionEl);
                }
            });
        } else {
            _.each($dishes, el => {
                const $description = $(el).find('.s_product_catalog_dish_description');
                if ($description.hasClass('o_default_snippet_text')) {
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
});
