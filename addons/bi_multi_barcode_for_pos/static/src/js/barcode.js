odoo.define('bi_multi_barcode_for_pos.pos', function(require) {
	"use strict";

	const Registries = require('point_of_sale.Registries');
	var PosDB = require('point_of_sale.DB');
	var { Order, Orderline, PosGlobalState} = require('point_of_sale.models');

	const PoSPRoductBarcode = (PosGlobalState) => class PoSPRoductBarcode extends PosGlobalState {

		async _processData(loadedData) {
			await super._processData(...arguments);
			this._loadProductBarcode(loadedData['product.barcode']);
			console.log("loadedData--------------",loadedData)
			console.log("this--------------",this)
			
		}
		_loadProductBarcode(barcodes){
			var self=this;
			self.barcode_by_name={};
			_.each(barcodes, function(barcode){
				self.barcode_by_name[barcode.barcode] = barcode;
			});

		}
	}

	Registries.Model.extend(PosGlobalState, PoSPRoductBarcode);

	PosDB.include({
		init: function(options){
			this._super.apply(this, arguments);
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
			if (product.product_barcodes) {
				str += '|' + product.product_barcodes;
			}
			if (product.description_sale) {
				str += '|' + product.description_sale;
			}
			str  = product.id + ':' + str.replace(/:/g,'') + '\n';
			return str;
		},
	});


});
