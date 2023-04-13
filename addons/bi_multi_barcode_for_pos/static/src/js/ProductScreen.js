odoo.define('bi_multi_barcode_for_pos.BiProductScreen', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const Registries = require('point_of_sale.Registries');


	const BiProductScreen = (ProductScreen) =>
		class extends ProductScreen {
			async _barcodeProductAction(code) {
				let check = this.scan_prod_barcode(code.base_code)
				if(check == false){
					super._barcodeProductAction(code);
				}
			}

			scan_prod_barcode (parsed_code){
				let self = this;
				let selectedOrder = this.env.pos.get_order();
				let barcode = this.env.pos.barcode_by_name[parsed_code];
				if(barcode){
					let products = [];
					if(barcode.product_id){
						let product = this.env.pos.db.get_product_by_id(barcode.product_id[0]);
						if(product){
							selectedOrder.add_product(product,{quantity:1});
							return true;
						}else{
							return true;
						}
					}
					else if(barcode.product_tmpl_id){
						let list = self.env.pos.db.search_product_in_category(0,parsed_code);
						if(list.length ==1){
							selectedOrder.add_product(list[0], {quantity:1});
							return true;
						}else{
							return false;
						}
					}else{
						return false;
					}
				}
				return false;
			}
	};
	Registries.Component.extend(ProductScreen, BiProductScreen);
	return ProductScreen;

});
