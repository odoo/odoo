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

    modula.PosDB = modula.Class.extend({

        state:   'connecting',  // 'connecting' || 'connected' || 'failed'
        version:  1,
        name:    'openerp_pos_db',

        init: function(options){
            var open_request = indexedDB.open(this.name, this.version);
        },
        upgrade_db: function(oldversion, transaction){
            this.db = transaction.db;
            var productStore = this.db.createObjectStore("products", {keyPath: "id"});

            productStore.createIndex("ean13", "ean13", {unique:true});

            productStore.createIndex("name", "name", {unique:false});

            productStore.createIndex("category","category", {unique:false});

            var imageStore = this.db.createObjectStore("images", {keyPath: "id"});

            imageStore.createIndex("product_id", "product_id", {unique:true});
        },
        _add_data: function(store, data, result_callback){
            var transaction = this.db.transaction([store], IDBTransaction.READ_WRITE);

            transaction.oncomplete = function(event){ if(result_callback){ result_callback(event); }};

        },
        add_product: function(product){
        },
        get_product_by_ean: function(ean, result_callback){
        },
        get_product_by_category: function(category, result_callback){
        },
        get_product_image: function(product, result_callback){
        },
        search_product: function(query,result_callback){
        },
    });

}
