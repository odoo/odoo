/**
 * WIP : AS OF THIS COMMIT, THE INDEXEDB BACKEND IS IN A NON WORKING STATE
 *
 * This file contains an IndexedDB (html5 database) backend for the Point Of Sale.
 * The IDB is used to store the list of products and especially their thumbnails, which may
 * not fit in the localStorage. 
 * The IDB offers a big performance boost for products lookup, but not so much for search as
 * searching is not yet implemented in the IndexedDB API and must be performed manually in JS.
 *
 * this file also contains a localstorage implementation of the database to be used by browsers
 * that don't support the indexeddb api.
 * 
 */
function openerp_pos_db(instance, module){ 

    function importIndexedDB(){
        if('indexedDB' in window){
            return true;
        }else if('webkitIndexedDB' in window){
            window.indexedDB      = window.webkitIndexedDB;
            window.IDBCursor      = window.webkitIDBCursor;
            window.IDBDatabase    = window.webkitIDBDatabase;
            window.IDBDatabaseError     = window.webkitIDBDatabaseError;
            window.IDBDatabaseException = window.webkitIDBDatabaseException;
            window.IDBFactory     = window.webkitIDBFactory;
            window.IDBIndex       = window.webkitIDBIndex;
            window.IDBKeyRange    = window.webkitIDBKeyRange;
            window.IDBObjectSrore = window.webkitIDBOjbectStore;
            window.IDBRequest     = window.webkitIDBRequest;
            window.IDBTransaction = window.webkitIDBTransaction;
        }else if('mozIndexedDB' in window){
            window.indexedDB      = window.mozIndexedDB;
        }else{
            throw new Error("DATABASE ERROR: IndexedDB not implemented. Please upgrade your web browser");
        }
    }
    importIndexedDB();

    module.PosDB = instance.web.Class.extend({

        version:  1,
        name:    'openerp_pos_db',
        limit:    50,

        init: function(options){
            var self = this;
            options = options || {};

            this.version = options.version || this.version;
            this.name = options.name || this.name;

            var open_request = indexedDB.open(this.name, this.version);

            open_request.onblocked = function(event){
                throw new Error("DATABASE ERROR: request blocked.");
            };

            // new API (firefox) 
            open_request.onupgradeneeded = function(event){
                console.log('using new API');
                var transaction = open_request.transaction;
                self._upgrade_db(event.oldVersion,transaction);
            };

            open_request.onsuccess = function(event){
                console.log('db',self.db);
                self.db = open_request.result;
                var oldVersion = Number(self.db.version);

                if(oldVersion !== self.version){
                    // if we get to this point, it means that onupgradeneeded hasn't been called.
                    // so we try the old api (webkit)
                    if(!self.db.setVersion){
                        throw new Error("DATABASE ERROR: database API is broken. Your web browser is probably out of date");
                    }
                    console.log('using old API');
                    var version_request = self.db.setVersion(self.version);
                    version_request.onsuccess = function(event){
                        var transaction = version_request.result;
                        self._upgrade_db(oldVersion, transaction);
                    };
                }
            };
        },
        _upgrade_db: function(oldversion, transaction){
            console.log('upgrade_db:',oldversion);

            this.db = transaction.db;
            var productStore = this.db.createObjectStore('products', {keyPath: 'id'});

            productStore.createIndex('ean13', 'ean13', {unique:true});

            productStore.createIndex('name', 'name', {unique:false});

            productStore.createIndex('category','category', {unique:false});

            var imageStore = this.db.createObjectStore('images', {keyPath: 'id'});

            var categoryStore = this.db.createObjectStore('categories', {keypath:'name'});
        },

        _add_data: function(store, data){
            var transaction = this.db.transaction([store], 'readwrite');
            var objectStore = transaction.objectStore(store);
            var request = objectStore.put(data);
        },
        /* adds a product to the database, replacing the original product if it is already present.
         * the product must be provided as a json as returned by the openerp backend 
         */
        add_product: function(product){
            if(product instanceof Array){
                for(var i = 0, len = product.length; i < len; i++){
                    this.add_product(product[i]);
                }
            }else{
                if(product.product_image_small){
                    var image = product.product_image_small;
                    var product = _.clone(product);
                    delete product['product_image_small'];
                    this._add_data('images', { id: product.id, image:image});
                }
                this._add_data('products',product);
            }
        },

        /* removes all the data in the database ! */
        clear: function(done_callback){
            var transaction = this.db.transaction(['products','images'],'readwrite');
            transaction.objectStore('products').clear();
            transaction.objectStore('images').clear();
            if(done_callback){
                transaction.oncomplete = function(){ done_callback(); };
            }
        },

        get_product_count: function(result_callback){
            this.db.transaction('products').objectStore('products').count().onsuccess = function(event){
                result_callback(event.target.result);
            };
        },

        get_image_count: function(result_callback){
            this.db.transaction('images').objectStore('images').count().onsuccess = function(event){
                result_callback(event.target.result);
            };
        },

        /* fetches a product with an id of 'id', returns the product as the first parameter
         * of the result_callback function
         */
        get_product_by_id:   function(id, result_callback){
            var transaction = this.db.transaction('products');
            var objectStore = transaction.objectStore('products');
            var request = objectStore.get(id);
            request.onsuccess = function(event){
                if(result_callback){
                    result_callback(event.target.result);
                }
            };
        },
        get_product_by_name: function(name, result_callback){
            var transaction = this.db.transaction('products');
            var objectStore = transaction.objectStore('products');
            var index       = objectStore.index('name');
            index.get(name).onsuccess = function(event){
                result_callback(event.target.result);
            };
        },
        /* fetches the product with the ean13 matching the one provided. returns the product
         * as the first parameter of the result_callback function
         */
        get_product_by_ean13: function(ean13, result_callback){
            var transaction = this.db.transaction('products');
            var objectStore = transaction.objectStore('products');
            var index       = objectStore.index('ean13');
            index.get(ean13).onsuccess = function(event){
                result_callback(event.target.result);
            };
        },
        /* fetches all products belonging to a category, and returns the list of products
         * as the first paramter of the result_callback function
         */
        get_product_by_category: function(category, result_callback){
            var transaction = this.db.transaction('products');
            var objectStore = transaction.objectStore('products');
            var index       = objectStore.index('category');
            var list = [];
            index.openCursor(IDBKeyRange.only(category)).onsuccess = function(event){
                var cursor = event.target.result;
                if(cursor){
                    list.push(cursor.value);
                    cursor.continue();
                }else{
                    result_callback(list);
                }
            };
        },
        /* Fetches a picture associated with a product. 
         * product: This is a product json object as returned by the openerp backend.
         * result_callback: a callback that gets the image data as parameter.
         */
        get_product_image: function(product, result_callback){
            var transaction = this.db.transaction('images');
            var objectStore = transaction.objectStore('images');
            var request = objectStore.get(product.id);
            request.onsuccess = function(event){
                result_callback(event.target.result.image);
            }
        },
        /* fields:  a string or a list of string representing the list of the fields that 
         *   will be searched. the values of those field must be a string.
         * query:   a string that will be matched in the content of one of the searched fields.
         * result_callback: a function that will be called with a list of all the products with
         *   a field that match the query.
         */
        search_product: function(fields,query,result_callback){
            var transaction = this.db.transaction('products');
            var objectStore = transaction.objectStore('products');
            var list = [];
            if(!(fields instanceof Array)){
                fields = [ fields ];
            }
            query = query.toLowerCase();
            objectStore.openCursor().onsuccess = function(event){
                var cursor = event.target.result;
                if(cursor){
                    var obj = cursor.value;
                    for(var i = 0, len = fields.length; i < len; i++){
                        if(obj[fields[i]].toLowerCase().indexOf(query) != -1){
                            list.push(obj);
                            break;
                        }
                    }
                    cursor.continue();
                }else{
                    result_callback(list);
                }
            }
        },
        /* the callback function will be called with all products as parameter, by increasing id.
         * if the callback returns 'break' the iteration will stop
         */
        for_all_products: function(callback){
            var transaction = this.db.transaction('products');
            var objectStore = transaction.objectStore('products');
            objectStore.openCursor().onsuccess = function(event){
                var cursor = event.target.result;
                if(cursor){
                    var ret = callback(cursor.value);
                    if(ret !== 'break'){
                        cursor.continue();
                    }
                }
            };
        },
        /* the callback function will be called with all products as parameter by increasing id.
         * if the callback returns 'break', the iteration will stop
         * if the callback returns a product object, it will be inserted in the db, possibly 
         * overwriting an existing product. The intended usage is for the callback to return a 
         * modified version version of the product with the same id. Anything else and you're on your own.
         */
        modify_all_products: function(callback){
            var transaction = this.db.transaction('products','readwrite');
            var objectStore = transaction.objectStore('products');
            objectStore.openCursor().onsuccess = function(event){
                var cursor = event.target.result;
                if(cursor){
                    var ret = callback(cursor.value);
                    if(ret === undefined || ret === null){
                        cursor.continue();
                    }else if(ret === 'break'){
                        return;
                    }else{
                        objectStore.put(ret);
                    }
                }
            };
        },
    });
    window.PosDB = module.PosDB;

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
            this.products = this.name + '_products';
            this.categories = this.name + '_categories';

            //products cache put the data in memory to avoid roundtrips to the localstorage
            this.products_cache = null;
            this.categories_cache = null;

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
        /* this internal method returns from disc a dictionary associating ids to the products */
        _get_products: function(){
            if(this.products_cache){
                return this.products_cache;
            }
            var products = localStorage[this.products];
            if(products){
                return JSON.parse(products) || {};
            }else{
                return {};
            }
        },
        /* this internal method saves a dictionary associating ids to product to the disc */
        _set_products: function(products){
            localStorage[this.products] = JSON.stringify(products);
            this.products_cache = products;
        },
        /* this internal method returns from disc a dictionary associating ids to the categories */
        _get_categories: function(){
            if(this.categories_cache){
                return this.categories_cache;
            }
            var categories = localStorage[this.categories];
            if(categories){
                return JSON.parse(categories) || {};
            }else{
                return {};
            }
        },
        /* this internal method saves to disc an array associating ids to the categories */
        _set_categories: function(categories){
            localStorage[this.categories] = JSON.stringify(categories);
            this.categories_cache = categories;
        },
        add_products: function(products){
            var stored_products = this._get_products();
            var stored_categories = this._get_categories();

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
            this._set_products(stored_products);
            this._set_categories(stored_categories);
        },
        /* removes all the data from the database. TODO : being able to selectively remove data */
        clear: function(done_callback){
            localStorage.removeItem(this.products);
            localStorage.removeItem(this.categories);
            if(done_callback){
                done_callback();
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
        get_product_count: function(result_callback){
            result_callback(this._count_props(this._get_products()));
        },
        get_product_by_id: function(id, result_callback){
            var products = this._get_products();
            result_callback( products[id] );
        },
        get_product_by_name: function(name, result_callback){
            var products = this._get_products();
            for(var i in products){
                if(products[i] && products[i].name === name){
                    result_callback(products[i]);
                    return;
                }
            }
            result_callback(undefined);
        },
        get_product_by_ean13: function(ean13, result_callback){
            var products = this._get_products();
            for(var i in products){
                if( products[i] && products[i].ean13 === ean13){
                    result_callback(products[i]);
                    return;
                }
            }
            result_callback(undefined);
        },
        get_product_by_category: function(category_id, result_callback){
            var stored_categories = this._get_categories();
            var stored_products   = this._get_products();
            var product_ids  = stored_categories[category_id];
            var list = [];
            for(var i = 0, len = Math.min(product_ids.length,this.limit); i < len; i++){
                list.push(stored_products[product_ids[i]]);
            }
            result_callback(list);
        },
        /* returns as a parameter of the result_callback function a list of products with :
         * - a category that is or is a child of category_id,
         * - a field in fields that contains a value that contains the query
         * If a search is started before the previous has returned, the previous search may be cancelled
         * (and the corresponding result_callback never called) 
         */
        search_product_in_category: function(category_id, fields, query, result_callback){
            var self = this;
            var stored_categories = this._get_categories();
            var stored_products   = this._get_products();
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
            result_callback(list);
        },
        // TODO move the order storage from the crappy DAO in pos_models.js
        add_order: function(order,done_callback){
        },
        remove_order: function(order_id, done_callback){
        },
        get_orders: function(result_callback){
        },
    });

    window.PosLS = module.PosLS;
}
