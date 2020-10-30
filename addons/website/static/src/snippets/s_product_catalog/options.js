
odoo.define('website.s_product_catalog_options', function (require) {
'use strict';

const core = require('web.core');
const snippetOptions = require('web_editor.snippets.options');

const _t = core._t;

snippetOptions.registry.ProductCatalog = snippetOptions.SnippetOptionWidget.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Show/hide descriptions.
     *
     * @see this.selectClass for parameters
     */
    toggleDescription: async function (previewMode, widgetValue, params) {
        const $dishes = this.$('.s_product_catalog_dish');
        const $name = $dishes.find('.s_product_catalog_dish_name');
        $name.toggleClass('s_product_catalog_dish_dot_leaders', !widgetValue);
        if (widgetValue) {
            _.each($dishes, el => {
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
            _.each($dishes, el => {
                const $description = $(el).find('.s_product_catalog_dish_description');
                if ($description.hasClass('o_default_snippet_text') || $description.find('.o_default_snippet_text').length) {
                    $description.remove();
                } else {
                    $description.addClass('d-none');
                }
            });
        }
        if (previewMode === false) await this.updateChangesInWysiwyg();
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
