odoo.define('pos_multi_barcodes', function (require) {
"use strict";
    var PosDB = require('point_of_sale.DB');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { PosGlobalState, Orderline } = require('point_of_sale.models');
    

    const MultiBarcodePosGlobalState = (PosGlobalState) => class MultiBarcodePosGlobalState extends PosGlobalState {
        async _processData(loadedData) {
            await super._processData(...arguments);
            this.multi_barcode_options = loadedData['pos.multi.barcode.options'];
        }
    }
    Registries.Model.extend(PosGlobalState, MultiBarcodePosGlobalState);

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
                if(product.pos_multi_barcode_option){
                    var barcode_list = $.parseJSON(product.barcode_options);
                    for(var k=0;k<barcode_list.length;k++){
                        this.product_by_barcode[barcode_list[k]] = product;
                    }
                }
            }
        },
    });



    const PosMultiBarcodeOrderline = (Orderline) => class PosMultiBarcodeOrderline extends Orderline {
        constructor() {
            super(...arguments);
            this.new_uom = '';
        }

        set_pro_uom(uom_id){
            this.new_uom = this.pos.units_by_id[uom_id];
            // this.trigger('change',this);
        }

        get_unit(){
            var unit_id = this.product.uom_id;
            if(!unit_id){
                return undefined;
            }
            unit_id = unit_id[0];
            if(!this.pos){
                return undefined;
            }
            return this.new_uom == '' ? this.pos.units_by_id[unit_id] : this.new_uom;
        }

        export_as_JSON(){
            var unit_id = this.product.uom_id;
            var json = super.export_as_JSON(...arguments);
            json.product_uom = this.new_uom == '' ? unit_id[0] : this.new_uom.id;
            return json;
        }
        init_from_JSON(json){
            super.init_from_JSON(...arguments);
            this.new_uom = json.new_uom;
        }


    }
    Registries.Model.extend(Orderline, PosMultiBarcodeOrderline);

    const PosResProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            async _barcodeProductAction(code) {
                const product = this.env.pos.db.get_product_by_barcode(code.base_code)
                if (!product) {
                    return this._barcodeErrorAction(code);
                }
                const options = await this._getAddProductOptions(product);
                // Do not proceed on adding the product when no options is returned.
                // This is consistent with _clickProduct.
                if (!options) return;

                // update the options depending on the type of the scanned code
                if (code.type === 'price') {
                    Object.assign(options, { price: code.value });
                } else if (code.type === 'weight') {
                    Object.assign(options, {
                        quantity: code.value,
                        merge: false,
                    });
                } else if (code.type === 'discount') {
                    Object.assign(options, {
                        discount: code.value,
                        merge: false,
                    });
                }
                this.currentOrder.add_product(product,  options)
                var line = this.currentOrder.get_last_orderline();
                var pos_multi_op = this.env.pos.multi_barcode_options;
                for(var i=0;i<pos_multi_op.length;i++){
                    if(pos_multi_op[i].name == code.code){
                        line.set_quantity(pos_multi_op[i].qty);
                        line.set_unit_price(pos_multi_op[i].price);
                        line.set_pro_uom(pos_multi_op[i].unit[0]);
                        line.price_manually_set = true;
                    }
                }
            }
        };

    Registries.Component.extend(ProductScreen, PosResProductScreen);
});

