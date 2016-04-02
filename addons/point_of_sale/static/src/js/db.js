odoo.define('point_of_sale.DB', function (require) {
"use strict";

var core = require('web.core');
/* The PosDB holds reference to data that is either
 * - static: does not change between pos reloads
 * - persistent : must stay between reloads ( orders )
 */

var PosDB = core.Class.extend({
    name: 'openerp_pos_db', //the prefix of the localstorage data
    limit: 100,  // the maximum number of results returned by a search
    init: function(options){
        options = options || {};
        this.name = options.name || this.name;
        this.limit = options.limit || this.limit;
        
        if (options.uuid) {
            this.name = this.name + '_' + options.uuid;
        }

        //cache the data in memory to avoid roundtrips to the localstorage
        this.cache = {};

        this.product_by_id = {};
        this.product_by_barcode = {};
        this.product_by_category_id = {};

        this.partner_sorted = [];
        this.partner_by_id = {};
        this.partner_by_barcode = {};
        this.partner_search_string = "";
        this.partner_write_date = null;

        this.category_by_id = {};
        this.root_category_id  = 0;
        this.category_products = {};
        this.category_ancestors = {};
        this.category_childs = {};
        this.category_parent    = {};
        this.category_search_string = {};
        this.packagings_by_id = {};
        this.packagings_by_product_tmpl_id = {};
        this.packagings_by_barcode = {};
    },

    /* 
     * sets an uuid to prevent conflict in locally stored data between multiple databases running
     * in the same browser at the same origin (Doing this is not advised !)
     */
    set_uuid: function(uuid){
        this.name = this.name + '_' + uuid;
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
        len = categories.length;
        for(i=0; i < len; i++){
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
    category_contains: function(categ_id, product_id) {
        var product = this.product_by_id[product_id];
        if (product) {
            var cid = product.pos_categ_id[0];
            while (cid && cid !== categ_id){
                cid = this.category_parent[cid];
            }
            return !!cid;
        }
        return false;
    },
    /* loads a record store from the database. returns default if nothing is found */
    load: function(store,deft){
        if(this.cache[store] !== undefined){
            return this.cache[store];
        }
        var data = localStorage[this.name + '_' + store];
        if(data !== undefined && data !== ""){
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
    _product_search_string: function(product){
        var str = product.display_name;
        if (product.barcode) {
            str += '|' + product.barcode;
        }
        if (product.default_code) {
            str += '|' + product.default_code;
        }
        if (product.description) {
            str += '|' + product.description;
        }
        if (product.description_sale) {
            str += '|' + product.description_sale;
        }
        var packagings = this.packagings_by_product_tmpl_id[product.product_tmpl_id] || [];
        for (var i = 0; i < packagings.length; i++) {
            str += '|' + packagings[i].barcode;
        }
        str  = product.id + ':' + str.replace(/:/g,'') + '\n';
        return str;
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
            product.product_tmpl_id = product.product_tmpl_id[0];
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
            if(product.barcode){
                this.product_by_barcode[product.barcode] = product;
            }
        }
    },
    add_packagings: function(packagings){
        for(var i = 0, len = packagings.length; i < len; i++){
            var pack = packagings[i];
            this.packagings_by_id[pack.id] = pack;
            if(!this.packagings_by_product_tmpl_id[pack.product_tmpl_id[0]]){
                this.packagings_by_product_tmpl_id[pack.product_tmpl_id[0]] = [];
            }
            this.packagings_by_product_tmpl_id[pack.product_tmpl_id[0]].push(pack);
            if(pack.barcode){
                this.packagings_by_barcode[pack.barcode] = pack;
            }
        }
    },
    _partner_search_string: function(partner){
        var str =  partner.name;
        if(partner.barcode){
            str += '|' + partner.barcode;
        }
        if(partner.address){
            str += '|' + partner.address;
        }
        if(partner.phone){
            str += '|' + partner.phone.split(' ').join('');
        }
        if(partner.mobile){
            str += '|' + partner.mobile.split(' ').join('');
        }
        if(partner.email){
            str += '|' + partner.email;
        }
        str = '' + partner.id + ':' + str.replace(':','') + '\n';
        return str;
    },
    add_partners: function(partners){
        var updated_count = 0;
        var new_write_date = '';
        var partner;
        for(var i = 0, len = partners.length; i < len; i++){
            partner = partners[i];

            if (    this.partner_write_date && 
                    this.partner_by_id[partner.id] &&
                    new Date(this.partner_write_date).getTime() + 1000 >=
                    new Date(partner.write_date).getTime() ) {
                // FIXME: The write_date is stored with milisec precision in the database
                // but the dates we get back are only precise to the second. This means when
                // you read partners modified strictly after time X, you get back partners that were
                // modified X - 1 sec ago. 
                continue;
            } else if ( new_write_date < partner.write_date ) { 
                new_write_date  = partner.write_date;
            }
            if (!this.partner_by_id[partner.id]) {
                this.partner_sorted.push(partner.id);
            }
            this.partner_by_id[partner.id] = partner;

            updated_count += 1;
        }

        this.partner_write_date = new_write_date || this.partner_write_date;

        if (updated_count) {
            // If there were updates, we need to completely 
            // rebuild the search string and the barcode indexing

            this.partner_search_string = "";
            this.partner_by_barcode = {};

            for (var id in this.partner_by_id) {
                partner = this.partner_by_id[id];

                if(partner.barcode){
                    this.partner_by_barcode[partner.barcode] = partner;
                }
                partner.address = (partner.street || '') +', '+ 
                                  (partner.zip || '')    +' '+
                                  (partner.city || '')   +', '+ 
                                  (partner.country_id[1] || '');
                this.partner_search_string += this._partner_search_string(partner);
            }
        }
        return updated_count;
    },
    get_partner_write_date: function(){
        return this.partner_write_date || "1970-01-01 00:00:00";
    },
    get_partner_by_id: function(id){
        return this.partner_by_id[id];
    },
    get_partner_by_barcode: function(barcode){
        return this.partner_by_barcode[barcode];
    },
    get_partners_sorted: function(max_count){
        max_count = max_count ? Math.min(this.partner_sorted.length, max_count) : this.partner_sorted.length;
        var partners = [];
        for (var i = 0; i < max_count; i++) {
            partners.push(this.partner_by_id[this.partner_sorted[i]]);
        }
        return partners;
    },
    search_partner: function(query){
        try {
            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,'.');
            query = query.replace(' ','.+');
            var re = RegExp("([0-9]+):.*?"+query,"gi");
        }catch(e){
            return [];
        }
        var results = [];
        for(var i = 0; i < this.limit; i++){
            var r = re.exec(this.partner_search_string);
            if(r){
                var id = Number(r[1]);
                results.push(this.get_partner_by_id(id));
            }else{
                break;
            }
        }
        return results;
    },
    /* removes all the data from the database. TODO : being able to selectively remove data */
    clear: function(){
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
    get_product_by_barcode: function(barcode){
        if(this.product_by_barcode[barcode]){
            return this.product_by_barcode[barcode];
        }
        var pack = this.packagings_by_barcode[barcode];
        if(pack){
            return this.product_by_id[pack.product_tmpl_id[0]];
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
     * - a name, package or barcode containing the query (case insensitive) 
     */
    search_product_in_category: function(category_id, query){
        try {
            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,'.');
            query = query.replace(/ /g,'.+');
            var re = RegExp("([0-9]+):.*?"+query,"gi");
        }catch(e){
            return [];
        }
        var results = [];
        for(var i = 0; i < this.limit; i++){
            var r = re.exec(this.category_search_string[category_id]);
            if(r){
                var id = Number(r[1]);
                results.push(this.get_product_by_id(id));
            }else{
                break;
            }
        }
        return results;
    },
    /* from a product id, and a list of category ids, returns
     * true if the product belongs to one of the provided category
     * or one of its child categories.
     */
    is_product_in_category: function(category_ids, product_id) {
        if (!(category_ids instanceof Array)) {
            category_ids = [category_ids];
        }
        var cat = this.get_product_by_id(product_id).pos_categ_id[0];
        while (cat) {
            for (var i = 0; i < category_ids.length; i++) {
                if (cat == category_ids[i]) {   // The == is important, ids may be strings
                    return true;
                }
            }
            cat = this.get_category_parent_id(cat);
        }
        return false;
    },

    /* paid orders */
    add_order: function(order){
        var order_id = order.uid;
        var orders  = this.load('orders',[]);

        // if the order was already stored, we overwrite its data
        for(var i = 0, len = orders.length; i < len; i++){
            if(orders[i].id === order_id){
                orders[i].data = order;
                this.save('orders',orders);
                return order_id;
            }
        }

        orders.push({id: order_id, data: order});
        this.save('orders',orders);
        return order_id;
    },
    remove_order: function(order_id){
        var orders = this.load('orders',[]);
        orders = _.filter(orders, function(order){
            return order.id !== order_id;
        });
        this.save('orders',orders);
    },
    remove_all_orders: function(){
        this.save('orders',[]);
    },
    get_orders: function(){
        return this.load('orders',[]);
    },
    get_order: function(order_id){
        var orders = this.get_orders();
        for(var i = 0, len = orders.length; i < len; i++){
            if(orders[i].id === order_id){
                return orders[i];
            }
        }
        return undefined;
    },

    /* working orders */
    save_unpaid_order: function(order){
        var order_id = order.uid;
        var orders = this.load('unpaid_orders',[]);
        var serialized = order.export_as_JSON();

        for (var i = 0; i < orders.length; i++) {
            if (orders[i].id === order_id){
                orders[i].data = serialized;
                this.save('unpaid_orders',orders);
                return order_id;
            }
        }

        orders.push({id: order_id, data: serialized});
        this.save('unpaid_orders',orders);
        return order_id;
    },
    remove_unpaid_order: function(order){
        var orders = this.load('unpaid_orders',[]);
        orders = _.filter(orders, function(o){
            return o.id !== order.uid;
        });
        this.save('unpaid_orders',orders);
    },
    remove_all_unpaid_orders: function(){
        this.save('unpaid_orders',[]);
    },
    get_unpaid_orders: function(){
        var saved = this.load('unpaid_orders',[]);
        var orders = [];
        for (var i = 0; i < saved.length; i++) {
            orders.push(saved[i].data);
        }
        return orders;
    },
});

return PosDB;

});

