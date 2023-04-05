odoo.define('pos_multi_barcode', function (require) {
"use strict";


    var PosDB = require('point_of_sale.DB');

    PosDB.include({
        init: function(options){
            var self = this;
            this.product_barcode_option_list = {};
            this._super(options);

        },
        add_products: function(products){
            var self = this;
            this._super(products); 
            for(var i = 0, len = products.length; i < len; i++){
                var product = products[i];
                var barcode_list = $.parseJSON(product.pos_multi_barcode_list);
                for(var k=0;k<barcode_list.length;k++){
                    this.product_by_barcode[barcode_list[k]] = product;
                }
            }
        },
    });
});

