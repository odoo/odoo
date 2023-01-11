odoo.define('fg_custom.ProductScreen', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');

    const FGProductScreen = ProductScreen =>
        class extends ProductScreen {

            async _onClickPay() {
                var order = this.env.pos.get_order();
                const currentClient = order.get_client();
                var lines_to_recompute = false;
                if(order.rewardsContainer && order.rewardsContainer._rewards){
                    _.each(order.rewardsContainer._rewards, function (line) {
                        if(line && line[0] && line[0].program && line[0].program.fg_discount_type){
                            if(line[0].program.fg_discount_type == 'is_pwd_discount' || line[0].program.fg_discount_type == 'is_senior_discount'){
                                lines_to_recompute = true;
                            }
                        }
                    });
                }
                if(lines_to_recompute){
                    if (currentClient) {
                    }else{
                        this.showPopup('ErrorPopup', {
                            title: this.env._t("Set customer"),
                            body: this.env._t("This order not available customer, discount line available on order"),
                        });
                        return;
                    }
                }
                await super._onClickPay();
            }

        };

    Registries.Component.extend(ProductScreen, FGProductScreen);
    return ProductScreen;
});
