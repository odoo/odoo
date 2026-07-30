/** @odoo-module **/
import { rpc } from '@web/core/network/rpc';
import publicWidget from "@web/legacy/js/public/public_widget";
// loads product data from the server and populates a dropdown menu with the received product information
publicWidget.registry.product_load = publicWidget.Widget.extend({
    selector: '#product',
    start: function() {
            var self = this;
            return this._super.apply(this, arguments).then(function() {
                self._loadProducts();
            });
        },
         _loadProducts: function() {
            var self = this;
            rpc('/product').then(function(res) {
                var ar = res;
                self.$el.find('#product').prevObject.empty();
                $(ar).each(function(i) {
                    self.$el.find('#product').prevObject.append("<option value=" + ar[i].id + ">" + ar[i].name + "</option>");
                });
            });
        },
});
