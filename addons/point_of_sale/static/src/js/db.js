function openerp_pos_db(instance, module){ 

    /* The db module was intended to be used to store all the data needed to run the Point
     * of Sale in offline mode. (Products, Categories, Orders, ...) It would also use WebSQL 
     * or IndexedDB to make the searching and sorting products faster. It turned out not to be 
     * a so good idea after all. 
     * 
     * First it is difficult to make the Point of Sale truly independant of the server. A lot
     * of functionality cannot realistically run offline, like generating invoices. 
     *
     * IndexedDB turned out to be complicated and slow as hell, and loading all the data at the
     * start made the point of sale take forever to load over small connections. 
     *
     * LocalStorage has a hard 5.0MB on chrome. For those kind of sizes, it is just better 
     * to put the data in memory and it's not too big to download each time you launch the PoS.
     *
     * So at this point we are dropping the support for offline mode, and this module doesn't really
     * make sense anymore. But if at some point you want to store millions of products and if at
     * that point indexedDB has improved to the point it is usable, you can just implement this API. 
     *
     * You would also need to change the way the models are loaded at the start to not reload all your
     * product data. 
     */ 

    /* PosLS is a localstorage based implementation of the point of sale database.
     * FIXME: The Products definitions and categories are stored on the locastorage even tough they're 
     * always reloaded at launch. This could induce a slowdown because the data needs to be reparsed from
     * JSON before each operation. If you have a huge amount of products (around 25000) it can also 
     * blow the 5.0MB localstorage limit. 
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

            this.product_by_id = {};
            this.product_by_ean13 = {};
            this.product_by_category_id = {};

            this.category_by_id = {};
            this.root_category_id  = 0;
            this.category_products = {};
            this.category_ancestors = {};
            this.category_childs = {};
            this.category_parent    = {};
            this.category_search_string = {};
            this.packagings_by_id = {};
            this.packagings_by_product_id = {};
            this.packagings_by_ean13 = {};
        },
        /* returns the category object from its id. If you pass a list of id as parameters, you get
         * a list of category objects. 
         */  
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
            var str_data = JSON.stringify(data);
            localStorage[this.name + '_' + store] = JSON.stringify(data);
            this.cache[store] = data;
        },
        _product_search_string: function(product){
            var str = '' + product.id + ':' + product.name;
            if(product.ean13){
                str += '|' + product.ean13;
            }
            var packagings = this.packagings_by_product_id[product.id] || [];
            for(var i = 0; i < packagings.length; i++){
                str += '|' + packagings[i].ean;
            }
            return str + '\n';
        },
        add_products: function(products){
            var stored_categories = this.product_by_category_id;

            if(!products instanceof Array){
                products = [products];
            }
            for(var i = 0, len = products.length; i < len; i++){
                var product = products[i];
                var search_string = this._product_search_string(product);
                var categ_id = product.pos_categ_id ? product.pos_categ_id[0] : this.root_category_id;
                if(!stored_categories[categ_id]){
                    stored_categories[categ_id] = [];
                }
                stored_categories[categ_id].push(product.id);

                if(this.category_search_string[categ_id] === undefined){
                    this.category_search_string[categ_id] = '';
                }
                this.category_search_string[categ_id] += search_string;

                var ancestors = this.get_category_ancestors_ids(categ_id) || [];

                for(var j = 0, jlen = ancestors.length; j < jlen; j++){
                    var ancestor = ancestors[j];
                    if(! stored_categories[ancestor]){
                        stored_categories[ancestor] = [];
                    }
                    stored_categories[ancestor].push(product.id);

                    if( this.category_search_string[ancestor] === undefined){
                        this.category_search_string[ancestor] = '';
                    }
                    this.category_search_string[ancestor] += search_string; 
                }
                this.product_by_id[product.id] = product;
                if(product.ean13){
                    this.product_by_ean13[product.ean13] = product;
                }
            }
        },
        add_packagings: function(packagings){
            for(var i = 0, len = packagings.length; i < len; i++){
                var pack = packagings[i];
                this.packagings_by_id[pack.id] = pack;
                if(!this.packagings_by_product_id[pack.product_id[0]]){
                    this.packagings_by_product_id[pack.product_id[0]] = [];
                }
                this.packagings_by_product_id[pack.product_id[0]].push(pack);
                if(pack.ean13){
                    this.packagings_by_ean13[pack.ean13] = pack;
                }
            }
        },
        /* removes all the data from the database. TODO : being able to selectively remove data */
        clear: function(stores){
            for(var i = 0, len = arguments.length; i < len; i++){
                localStorage.removeItem(this.name + '_' + arguments[i]);
            }
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
            return this.product_by_id[id];
        },
        get_product_by_ean13: function(ean13){
            if(this.product_by_ean13[ean13]){
                return this.product_by_ean13[ean13];
            }
            var pack = this.packagings_by_ean13[ean13];
            if(pack){
                return this.product_by_id[pack.product_id[0]];
            }
            return undefined;
        },
        get_product_by_category: function(category_id){
            var product_ids  = this.product_by_category_id[category_id];
            var list = [];
            if (product_ids) {
                for (var i = 0, len = Math.min(product_ids.length, this.limit); i < len; i++) {
                    list.push(this.product_by_id[product_ids[i]]);
                }
            }
            return list;
        },
        /* returns a list of products with :
         * - a category that is or is a child of category_id,
         * - a name, package or ean13 containing the query (case insensitive) 
         */
        search_product_in_category: function(category_id, query){
            var re = RegExp("([0-9]+):.*?"+query,"gi");
            var results = [];
            for(var i = 0; i < this.limit; i++){
                r = re.exec(this.category_search_string[category_id]);
                if(r){
                    var id = Number(r[1]);
                    results.push(this.get_product_by_id(id));
                }else{
                    break;
                }
            }
            return results;
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
}
