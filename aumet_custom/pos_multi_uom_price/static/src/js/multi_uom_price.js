odoo.define('pos_multi_uom_price.UOMButton', function (require) {
    "use strict";

   const PosComponent = require('point_of_sale.PosComponent');
   const ProductScreen = require('point_of_sale.ProductScreen');
   const { useListener } = require('web.custom_hooks');
   const Registries = require('point_of_sale.Registries');

   class UOMButton extends PosComponent {
       constructor() {
           super(...arguments);
           useListener('click', this.onClick);
       }
       get selectedOrderline() {
	       return this.env.pos.get_order().get_selected_orderline();
       }
       async onClick() {
	       let line = this.selectedOrderline;
	       if (line) {
	         let pupList = Object.keys(line.pos.product_uom_price);
	         let product = line.product.product_tmpl_id;
	         if (line && pupList.find(element => element === product.toString())) {
		       const uomList = [ { } ];
		       let uomPrices = line.pos.product_uom_price[product].uom_id;
		       if (uomPrices) {
			       _.each(uomPrices, function(uomPrice){
				       uomList.push({
					       id:	uomPrice.id,
					       label:	uomPrice.pos.format_currency(uomPrice.price) +'/'+ uomPrice.name,
					       isSelected: true,
					       item:	uomPrice,
				       });
			       });
		       }
		       const { confirmed, payload: selectedUOM } = await this.showPopup("SelectionPopup", {
			       title: 'UOM',
			       list: uomList,
		       });

		       if (confirmed) {
			       this.selectedOrderline.set_uom({0:selectedUOM.id,1:selectedUOM.name});
			       this.selectedOrderline.price_manually_set = true;
			       this.selectedOrderline.set_unit_price(selectedUOM.price);

		       }
	         }
	       }
       }	   
   }
   UOMButton.template = 'UOMButton';
   ProductScreen.addControlButton ({
       component: UOMButton,
       condition: function () {
           return true;
       },
       position: ['before', 'SetPricelistButton'],
   });
   Registries.Component.add (UOMButton);
   return UOMButton;


});
