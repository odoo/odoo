odoo.define('fg_custom.ProductScreen', function(require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');

    const FGProductScreen = ProductScreen =>
        class extends ProductScreen {

            async _onClickPay() {
                var order = this.env.pos.get_order();

                var popupTitle = 'Validate Transaction';
                if(order.orderlines.length == 0){
                    this.showPopup("ErrorPopup", {
                       title: this.env._t(popupTitle),
                       body: this.env._t('Transaction must have at least 1 order line.'),
                    });
                }else{
                    const currentClient = order.get_client();
                    var lines_to_recompute = false;
                    var discount_type='';
                    var errorMsg='Customer is required and PWD ID of the customer must be filled out for this transaction';
                    if(order.rewardsContainer && order.rewardsContainer._rewards){
                        _.each(order.rewardsContainer._rewards, function (line) {
                            if(line && line[0] && line[0].program && line[0].program.fg_discount_type){
                                if(line[0].program.fg_discount_type == 'is_pwd_discount' || line[0].program.fg_discount_type == 'is_senior_discount'){
                                    lines_to_recompute = true;
                                    discount_type = line[0].program.fg_discount_type;
                                }
                            }
                        });
                    }
                    if(lines_to_recompute){
                        var errorMessage='';
                        if(discount_type=='is_senior_discount' && (currentClient==null || !currentClient.x_senior_id || currentClient.x_senior_id=='')){
                            errorMessage='Customer is required and Senior Citizen ID of the customer must be filled out for this transaction.'
                        }else if(discount_type=='is_pwd_discount' && (currentClient==null || !currentClient.x_pwd_id || currentClient.x_pwd_id=='')){
                            errorMessage='Customer is required and PWD ID of the customer must be filled out for this transaction.'
                        }
                        if (errorMessage!='') {
                            this.showPopup('ErrorPopup', {
                                title: this.env._t("Validate Customer"),
                                body: this.env._t(errorMessage),
                            });
                            return;
                        }
                    }
                    await super._onClickPay();
                }



            }

        };

    Registries.Component.extend(ProductScreen, FGProductScreen);
    return ProductScreen;
});
