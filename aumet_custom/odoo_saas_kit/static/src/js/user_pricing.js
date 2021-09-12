odoo.define('odoo_saas_kit.user_pricing', function (require) {
    "use strict";

    var publicWidget = require('web.public.widget');
    const wUtils = require('website.utils');

    publicWidget.registry.WebsiteSale.include({

        /**
         * Adds the number_of_user value for saas users.
         * @override
         */
        _submitForm: function () {
            let params = this.rootProduct;
            params.add_qty = params.quantity;
            params.number_of_user = this.$form.find('#number_of_user').val();

            params.product_custom_attribute_values = JSON.stringify(params.product_custom_attribute_values);
            params.no_variant_attribute_values = JSON.stringify(params.no_variant_attribute_values);
            
            if (this.isBuyNow) {
                params.express = true;
            }
            return wUtils.sendRequest('/shop/cart/update', params);
        },
    });

});