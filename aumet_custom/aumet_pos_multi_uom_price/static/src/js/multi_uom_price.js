odoo.define('pos_multi_uom_price.UOMButton', function (require) {
    "use strict";
    const Orderline = require('point_of_sale.Orderline');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    const AsplRetOrderlineInh = (Orderline) =>
        class extends Orderline {
            constructor() {
                super(...arguments);
                useListener('click-uom-button', this.onClick);
            }

            get selectedOrderline() {
                return this.env.pos.get_order().get_selected_orderline();
            }

            async onClick() {
                const {confirmed, payload: selectedUOMCategory} = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Select UOM'),
                    list: this.filter_uom_by_category,
                });

                if (confirmed) {
                    var self = this;
                    var order = self.env.pos.get_order();
                    let line = this.selectedOrderline;
                    let product = line.product.product_tmpl_id;
                    let uomPrices = line.pos.product_uom_price[product].uom_id;

                    order.get_selected_orderline().set_custom_uom_id(selectedUOMCategory.id);
                    let uom_price = {'price': 0, 'found': false}
                    if (uomPrices) {
                        _.each(uomPrices, function (uomPrice) {
                            if (uomPrice.name == selectedUOMCategory.name) {
                                uom_price.price = uomPrice.price;
                                uom_price.found = true;
                            }
                        });
                    }
                    if (uom_price.found) {
                        this.selectedOrderline.price_manually_set = true;
                        this.selectedOrderline.set_unit_price(uom_price.price);
                    } else {
                        var self = this;
                        var order = self.env.pos.get_order();
                        order.get_selected_orderline().set_custom_uom_id(selectedUOMCategory.id);
                        var res = order.get_selected_orderline().apply_uom();
                        if (self.env.pos.config.customer_display) {
                            order.mirror_image_data();
                        }
                        if (!res) {
                            alert("Something went to wrong!");
                        }
                        this.render();
                    }

                }
            }
        }
    Registries.Component.extend(Orderline, AsplRetOrderlineInh);

    return Orderline;
})
;
