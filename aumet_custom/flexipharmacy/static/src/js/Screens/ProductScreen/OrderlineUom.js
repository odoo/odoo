odoo.define('flexipharmacy.Orderline', function(require) {
    'use strict';
    
    const Orderline = require('point_of_sale.Orderline');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { posbus } = require('point_of_sale.utils');
    var core = require('web.core');
    var _t = core._t;

    const AsplRetOrderlineInh = (Orderline) => 
        class extends Orderline {
            constructor() {
                super(...arguments);
                useListener('click-uom-button', this.clickUomButton);
                useListener('click-to-open-note-text', this.clickOpenNoteText);
            }
            get selectedOrderline() {
                return this.env.pos.get_order().get_selected_orderline();
            }
            async clickOpenNoteText() {
                if (!this.selectedOrderline) return;
                const { confirmed, payload: inputNote } = await this.showPopup('ProductNotePopup', {
                    startingValue: this.selectedOrderline.get_product_note(),
                    title: this.env._t('Product Note'),
                });
                if (confirmed) {
                    this.selectedOrderline.set_product_note(inputNote);
                    var order = this.env.pos.get_order();
                    if(this.env.pos.config.customer_display){
                        order.mirror_image_data();
                    }
                }
            }
            async onClickDelete(orderline){
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Confirmation'),
                    body: this.env._t('Are you sure you want to unassign lot/serial number(s) ?'),
                });
                if (confirmed){
                    var pack_lot_lines = orderline.pack_lot_lines;
                    var cids = [];
                    for(let i=0; i < pack_lot_lines.length; i++){
                        let lot_line = pack_lot_lines.models[i];
                        cids.push(lot_line.cid);
                    }
                    for(let j in cids){
                        pack_lot_lines.get({cid: cids[j]}).remove();
                    }
                    _.each(orderline.get_serials(), function(serial){
                        if(serial.isSelected){
                            serial['isSelected'] = false;
                        }
                    });
                    this.render();
                }
            }
            get filter_uom_by_category(){
                var list = []
                for (var uom in this.env.pos.units){
                    if(this.env.pos.units[uom].category_id[0] == this.env.pos.get_order().selected_orderline.get_unit().category_id[0]){
                        list.push({
                            id: this.env.pos.units[uom].id,
                            label: this.env.pos.units[uom].name,
                            isSelected: this.env.pos.units[uom].id
                            ? this.env.pos.units[uom].id === this.env.pos.get_order().selected_orderline.get_unit().id
                            : false,
                            item: this.env.pos.units[uom],
                        });
                    }
                }
                return list;
            }
            async clickUomButton(event) {
                const { confirmed, payload: selectedUOMCategory } = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Select UOM'),
                    list: this.filter_uom_by_category,
                }); 
                if (confirmed){
                    var self = this;
                    var order = self.env.pos.get_order();
                    order.get_selected_orderline().set_custom_uom_id(selectedUOMCategory.id);
                    var res = order.get_selected_orderline().apply_uom();
                    if(self.env.pos.config.customer_display){
                        order.mirror_image_data();
                    }
                    if(!res){
                        alert("Something went to wrong!");
                    }
                    this.render();
                }
            }
            async showIngredientPopup(orderline){
                this.env.pos.get_order().select_orderline(orderline);
                var ingredients = []
                if(this.env.pos.get_order().get_selected_orderline().get_orderline_ingredients()){
                    ingredients = this.env.pos.get_order().get_selected_orderline().get_orderline_ingredients();
                }else{
                    _.each(this.env.pos.active_ingredients, function(ingredient) {
                        if(_.contains(orderline.product.active_ingredient_ids, ingredient.id)){
                            ingredient['isSelected'] = false;
                            ingredients.push(ingredient)
                        }
                    });
                }
                if(ingredients.length > 0){
                    const { confirmed, payload: Lines } = await this.showPopup('IngredientPopup', {
                        ingredients : ingredients,
                        title: this.env._t('Add Ingredients'),
                    });
                    if(confirmed){
                        this.env.pos.get_order().get_selected_orderline().set_orderline_ingredients(Lines);
                        let selectedLines = []
                        _.each(Lines, function(ingredient){
                            if(ingredient.isSelected){
                                selectedLines.push(ingredient)
                            }
                        });
                        this.env.pos.get_order().get_selected_orderline().set_selected_orderline_ingredients(selectedLines)
                    }
                }
            }
        }

    Registries.Component.extend(Orderline, AsplRetOrderlineInh);

    return Orderline;
});
