odoo.define('pos_cache.pos_cache', function (require) {
"use strict";

var models = require('point_of_sale.models');
var core = require('web.core');
var rpc = require('web.rpc');
var _t = core._t;

var posmodel_super = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    load_server_data: function () {
        var self = this;

        var product_index = _.findIndex(this.models, function (model) {
            return model.model === "product.product";
        });

        var product_model = self.models[product_index];

        // We don't want to load product.product the normal
        // uncached way, so get rid of it.
        if (product_index !== -1) {
            this.models.splice(product_index, 1);
        }
        return posmodel_super.load_server_data.apply(this, arguments).then(function () {
          // Give both the fields and domain to pos_cache in the
          // backend. This way we don't have to hardcode these
          // values in the backend and they automatically stay in
          // sync with whatever is defined (and maybe extended by
          // other modules) in js.
          var product_fields =  typeof product_model.fields === 'function'  ? product_model.fields(self)  : product_model.fields;
          var product_domain =  typeof product_model.domain === 'function'  ? product_model.domain(self)  : product_model.domain;
            var records = rpc.query({
                    model: 'pos.config',
                    method: 'get_products_from_cache',
                    args: [self.pos_session.config_id[0], product_fields, product_domain],
                });
            self.chrome.loading_message(_t('Loading') + ' product.product', 1);
            return records.then(function (products) {
                self.db.add_products(_.map(products, function (product) {
                    product.categ = _.findWhere(self.product_categories, {'id': product.categ_id[0]});
                    return new models.Product({}, product);
                }));
            });
        });
    },
});

});
