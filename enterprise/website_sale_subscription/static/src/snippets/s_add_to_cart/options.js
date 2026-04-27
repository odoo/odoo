/** @odoo-module **/

import options from '@web_editor/js/editor/snippets.options';

options.registry.AddToCart.includes({

    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        switch (widgetName) {
            case 'product_plan_id': {
                return this.$target[0].dataset.productTemplate && this._variantIds().length > 1;
            }
        }
        return this._super(...arguments);
    },

})
