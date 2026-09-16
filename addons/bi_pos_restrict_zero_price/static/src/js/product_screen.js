odoo.define('bi_pos_restrict_zero_price.ProductScreen', function (require) {
    'use strict';
    const ProductScreen = require('point_of_sale.ProductScreen');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');
    var core = require('web.core');
    var rpc = require('web.rpc');
    var _t = core._t;
    const PosRestrictZeroProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
            }
            async _onClickPay() {
                let self = this;
                let order = this.env.pos.get_order();
                let lines = order.get_orderlines();
                let restrict_order = false;
                var product_names = ''
                if (this.env.pos.config.restrict_zero_price_line){
                    if (order && lines.length > 0 ){
                        _.each(lines, function (line) {
                            if (line.get_display_price() == 0.00){
                               restrict_order = true;
                               product_names += '-' + line.product.display_name + "\n"
                            }
                        });
                    }
                    else
                    {
                         restrict_order = true;
                    }
                    if (restrict_order){
                        if (product_names){
                            this.showPopup('ErrorPopup', {
                                'title': _t("Product With 0 Price"),
                                body:  _.str.sprintf(_t('You are not allowed to have the zero prices on the order line . %s'), product_names),

                            });
                        }
                        else{
                            this.showPopup('ErrorPopup', {
                                'title': _t("Empty Order"),
                                body:  _.str.sprintf(_t('There must be at least one product in your order before it can be validated.')),

                            });
                        }
                    }
                    else{
                        super._onClickPay();
                    }
                }
                else{
                    super._onClickPay();
                }
            }
        };

    Registries.Component.extend(ProductScreen, PosRestrictZeroProductScreen);

    return ProductScreen;
});