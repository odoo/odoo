function openerp_pos_db(instance, module){ 

    /* PosLS is a LocalStorage based implementation of the point of sale database,
       it performs better for few products, but does not scale beyond 500 products. 
       */
    module.PosLS = instance.web.Class.extend({
        name: 'openerp_pos_ls', //the prefix of the localstorage data
        limit: 100,  // the maximum number of results returned by a search
        init: function(options){
            options = options || {};
            this.name = options.name || this.name;
            this.limit = options.limit || this.limit;

            //cache the data in memory to avoid roundtrips to the localstorage
            this.cache = {};

            this.category_by_id = {};
            this.root_category_id  = 0;
            this.category_products = {};
            this.category_ancestors = {};
            this.category_childs = {};
            this.category_parent    = {};
        },
        /* returns the category object from its id */
        get_category_by_id: function(categ_id){
            if(categ_id instanceof Array){
                var list = [];
                for(var i = 0, len = categ_id.length; i < len; i++){
                    var cat = this.category_by_id[categ_id[i]];
                    if(cat){
                        list.push(cat);
                    }else{
                        console.error("get_category_by_id: no category has id:",categ_id[i]);
                    }
                }
                return list;
            }else{
                return this.category_by_id[categ_id];
            }
        },
        /* returns a list of the category's child categories ids, or an empty list 
         * if a category has no childs */
        get_category_childs_ids: function(categ_id){
            return this.category_childs[categ_id] || [];
        },
        /* returns a list of all ancestors (parent, grand-parent, etc) categories ids
         * starting from the root category to the direct parent */
        get_category_ancestors_ids: function(categ_id){
            return this.category_ancestors[categ_id] || [];
        },
        /* returns the parent category's id of a category, or the root_category_id if no parent.
         * the root category is parent of itself. */
        get_category_parent_id: function(categ_id){
            return this.category_parent[categ_id] || this.root_category_id;
        },
        /* adds categories definitions to the database. categories is a list of categories objects as
         * returned by the openerp server. Categories must be inserted before the products or the 
         * product/ categories association may (will) not work properly */
        add_categories: function(categories){
            var self = this;
            if(!this.category_by_id[this.root_category_id]){
                this.category_by_id[this.root_category_id] = {
                    id : this.root_category_id,
                    name : 'Root',
                };
            }
            for(var i=0, len = categories.length; i < len; i++){
                this.category_by_id[categories[i].id] = categories[i];
            }
            for(var i=0, len = categories.length; i < len; i++){
                var cat = categories[i];
                var parent_id = cat.parent_id[0] || this.root_category_id;
                this.category_parent[cat.id] = cat.parent_id[0];
                if(!this.category_childs[parent_id]){
                    this.category_childs[parent_id] = [];
                }
                this.category_childs[parent_id].push(cat.id);
            }
            function make_ancestors(cat_id, ancestors){
                self.category_ancestors[cat_id] = ancestors;

                ancestors = ancestors.slice(0);
                ancestors.push(cat_id);

                var childs = self.category_childs[cat_id] || [];
                for(var i=0, len = childs.length; i < len; i++){
                    make_ancestors(childs[i], ancestors);
                }
            }
            make_ancestors(this.root_category_id, []);
        },
        /* loads a record store from the database. returns default if nothing is found */
        load: function(store,deft){
            if(this.cache[store] !== undefined){
                return this.cache[store];
            }
            var data = localStorage[this.name + '_' + store];
            if(data !== undefined){
                data = JSON.parse(data);
                this.cache[store] = data;
                return data;
            }else{
                return deft;
            }
        },
        /* saves a record store to the database */
        save: function(store,data){
            localStorage[this.name + '_' + store] = JSON.stringify(data);
            this.cache[store] = data;
        },
        add_products: function(products){
            var stored_products = this.load('products',{}); 
            var stored_categories = this.load('categories',{});

            if(!products instanceof Array){
                products = [products];
            }
            for(var i = 0, len = products.length; i < len; i++){
                var product = products[i];
                var categ_id = product.pos_categ_id[0];
                if(!stored_categories[categ_id]){
                    stored_categories[categ_id] = [];
                }
                stored_categories[categ_id].push(product.id);
                var ancestors = this.get_category_ancestors_ids(categ_id) || [];

                for(var j = 0; j < ancestors.length; j++){
                    if(! stored_categories[ancestors[j]]){
                        stored_categories[ancestors[j]] = [];
                    }
                    stored_categories[ancestors[j]].push(product.id);
                }
                stored_products[product.id] = product;
            }
            this.save('products',stored_products);
            this.save('categories',stored_categories);
        },
        /* removes all the data from the database. TODO : being able to selectively remove data */
        clear: function(){
            localStorage.removeItem(this.name + '_products');
            localStorage.removeItem(this.name + '_categories');
        },
        /* this internal methods returns the count of properties in an object. */
        _count_props : function(obj){
            var count = 0;
            for(var prop in obj){
                if(obj.hasOwnProperty(prop)){
                    count++;
                }
            }
            return count;
        },
        get_product_by_id: function(id){
            return this.load('products',{})[id];
        },
        get_product_by_ean13: function(ean13){
            var products = this.load('products',{});
            for(var i in products){
                if( products[i] && products[i].ean13 === ean13){
                    return products[i];
                }
            }
            return undefined;
        },
        get_product_by_category: function(category_id){
            var stored_categories = this.load('categories',{});
            var stored_products   = this.load('products',{});
            var product_ids  = stored_categories[category_id];
            var list = [];
            for(var i = 0, len = Math.min(product_ids.length,this.limit); i < len; i++){
                list.push(stored_products[product_ids[i]]);
            }
            return list;
        },
        /* returns as a parameter of the result_callback function a list of products with :
         * - a category that is or is a child of category_id,
         * - a field in fields that contains a value that contains the query
         * If a search is started before the previous has returned, the previous search may be cancelled
         * (and the corresponding result_callback never called) 
         */
        search_product_in_category: function(category_id, fields, query){
            var self = this;
            var stored_categories = this.load('categories',{});
            var stored_products   = this.load('products',{});
            var product_ids       = stored_categories[category_id];
            var list = [];
            var count = 0;
            
            query = query.toString().toLowerCase();

            if(!(fields instanceof Array)){
                fields = [fields];
            }
            for(var i = 0, len = product_ids.length; i < len && count < this.limit; i++){
                var product = stored_products[product_ids[i]];
                for(var j = 0, jlen = fields.length; j < jlen; j++){
                    var field = product[fields[j]];
                    if(field === null || field === undefined){
                        continue;
                    }
                    field = field.toString().toLowerCase();
                    if(field.indexOf(query) != -1){
                        list.push(product);
                        count++;
                        break;
                    }
                }
            }
            return list;
        },
        add_order: function(order){
            var last_id = this.load('last_order_id',0);
            var orders  = this.load('orders',[]);
            orders.push({id: last_id + 1, data: order});
            this.save('last_order_id',last_id+1);
            this.save('orders',orders);
        },
        remove_order: function(order_id){
            var orders = this.load('orders',[]);
            orders = _.filter(orders, function(order){
                return order.id !== order_id;
            });
            this.save('orders',orders);
        },
        get_orders: function(){
            return this.load('orders',[]);
        },
    });
    /*
    module.LocalStorageDAO = instance.web.Class.extend({
        add_operation: function(operation) {
            var self = this;
            return $.async_when().pipe(function() {
                var tmp = self._get('oe_pos_operations', []);
                var last_id = self._get('oe_pos_operations_sequence', 1);
                tmp.push({'id': last_id, 'data': operation});
                self._set('oe_pos_operations', tmp);
                self._set('oe_pos_operations_sequence', last_id + 1);
            });
        },
        remove_operation: function(id) {
            var self = this;
            return $.async_when().pipe(function() {
                var tmp = self._get('oe_pos_operations', []);
                tmp = _.filter(tmp, function(el) {
                    return el.id !== id;
                });
                self._set('oe_pos_operations', tmp);
            });
        },
        get_operations: function() {
            var self = this;
            return $.async_when().pipe(function() {
                return self._get('oe_pos_operations', []);
            });
        },
        _get: function(key, default_) {
            var txt = localStorage['oe_pos_dao_'+key];
            if (! txt)
                return default_;
            return JSON.parse(txt);
        },
        _set: function(key, value) {
            localStorage['oe_pos_dao_'+key] = JSON.stringify(value);
        },
        reset_stored_data: function(){
            for(key in localStorage){
                if(key.indexOf('oe_pos_dao_') === 0){
                    delete localStorage[key];
                }
            }
            0497 53 82 88
        },
    });
    */

    window.PosLS = module.PosLS;
}
