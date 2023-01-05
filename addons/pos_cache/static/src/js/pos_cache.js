odoo.define('pos_cache.pos_cache', function (require) {
"use strict";

var { PosGlobalState } = require('point_of_sale.models');
const Registries = require('point_of_sale.Registries');


const PosCachePosGlobalState = (PosGlobalState) => class PosCachePosGlobalState extends PosGlobalState {
    async _getTotalProductsCount() {
        return this.env.services.rpc({
            model: 'pos.session',
            method: 'get_total_products_count',
            args: [[odoo.pos_session_id]],
            context: this.env.session.user_context,
        });
<<<<<<< HEAD
    }
    async _loadCachedProducts(start, end) {
        const products = await this.env.services.rpc({
            model: 'pos.session',
            method: 'get_cached_products',
            args: [[odoo.pos_session_id], start, end],
            context: this.env.session.user_context,
||||||| parent of 96eb344a0d0 (temp)

        var product_model = self.models[product_index];

        // We don't want to load product.product the normal
        // uncached way, so get rid of it.
        if (product_index !== -1) {
            this.models.splice(product_index, 1);
            this.product_model = product_model;
        }
        return posmodel_super.load_server_data.apply(this, arguments).then(function () {
          // Give both the fields and domain to pos_cache in the
          // backend. This way we don't have to hardcode these
          // values in the backend and they automatically stay in
          // sync with whatever is defined (and maybe extended by
          // other modules) in js.
          var product_fields =  typeof self.product_model.fields === 'function'  ? self.product_model.fields(self)  : self.product_model.fields;
          var product_domain =  typeof self.product_model.domain === 'function'  ? self.product_model.domain(self)  : self.product_model.domain;
            var limit_products_per_request = self.config.limit_products_per_request;
            var cur_request = 0;
            function next(resolve, reject){
                var domain = product_domain;
                if (limit_products_per_request){
                    domain = domain.slice();
                    // implement offset-limit via id, because "pos.cache"
                    // doesn't have such fields and we can add them in master
                    // branch only
                    domain.unshift(['id', '>', cur_request * limit_products_per_request],
                                   ['id', '<=', (cur_request + 1) * limit_products_per_request]);
                }
                return rpc.query({
                    model: 'pos.config',
                    method: 'get_products_from_cache',
                    args: [self.pos_session.config_id[0], product_fields, domain],
                }).then(function (products) {
                    self.db.add_products(_.map(products, function (product) {
                        product.categ = _.findWhere(self.product_categories, {'id': product.categ_id[0]});
                        product.pos = self;
                        return new models.Product({}, product);
                    }));
                    if (limit_products_per_request) {
                        cur_request++;
                        // check that we have more products
                        domain = product_domain.slice();
                        domain.unshift(['id', '>', cur_request * limit_products_per_request]);
                        rpc.query({
                            model: 'product.product',
                            method: 'search_read',
                            args: [domain, ['id']],
                            kwargs: {
                                limit: 1,
                            }
                        }).then(function (products) {
                            if (products.length){
                                next(resolve, reject);
                            } else {
                                resolve();
                            }
                        });
                    } else {
                        resolve();
                    }
                });
            }
            self.setLoadingMessage(_t('Loading') + ' product.product', 1);

            return new Promise((resolve, reject) => {
                next(resolve, reject);
            });
=======

        var product_model = self.models[product_index];

        // We don't want to load product.product the normal
        // uncached way, so get rid of it.
        if (product_index !== -1) {
            this.models.splice(product_index, 1);
            this.product_model = product_model;
        }
        return posmodel_super.load_server_data.apply(this, arguments).then(function () {
          // After loading the server data we have to add the product model as it is needed
          self.models.push(self.product_model)

          // Give both the fields and domain to pos_cache in the
          // backend. This way we don't have to hardcode these
          // values in the backend and they automatically stay in
          // sync with whatever is defined (and maybe extended by
          // other modules) in js.
          var product_fields =  typeof self.product_model.fields === 'function'  ? self.product_model.fields(self)  : self.product_model.fields;
          var product_domain =  typeof self.product_model.domain === 'function'  ? self.product_model.domain(self)  : self.product_model.domain;
            var limit_products_per_request = self.config.limit_products_per_request;
            var cur_request = 0;
            function next(resolve, reject){
                var domain = product_domain;
                if (limit_products_per_request){
                    domain = domain.slice();
                    // implement offset-limit via id, because "pos.cache"
                    // doesn't have such fields and we can add them in master
                    // branch only
                    domain.unshift(['id', '>', cur_request * limit_products_per_request],
                                   ['id', '<=', (cur_request + 1) * limit_products_per_request]);
                }
                return rpc.query({
                    model: 'pos.config',
                    method: 'get_products_from_cache',
                    args: [self.pos_session.config_id[0], product_fields, domain],
                }).then(function (products) {
                    self.db.add_products(_.map(products, function (product) {
                        product.categ = _.findWhere(self.product_categories, {'id': product.categ_id[0]});
                        product.pos = self;
                        return new models.Product({}, product);
                    }));
                    if (limit_products_per_request) {
                        cur_request++;
                        // check that we have more products
                        domain = product_domain.slice();
                        domain.unshift(['id', '>', cur_request * limit_products_per_request]);
                        rpc.query({
                            model: 'product.product',
                            method: 'search_read',
                            args: [domain, ['id']],
                            kwargs: {
                                limit: 1,
                            }
                        }).then(function (products) {
                            if (products.length){
                                next(resolve, reject);
                            } else {
                                resolve();
                            }
                        });
                    } else {
                        resolve();
                    }
                });
            }
            self.setLoadingMessage(_t('Loading') + ' product.product', 1);

            return new Promise((resolve, reject) => {
                next(resolve, reject);
            });
>>>>>>> 96eb344a0d0 (temp)
        });
        this._loadProductProduct(products);
    }
}
Registries.Model.extend(PosGlobalState, PosCachePosGlobalState);

});
