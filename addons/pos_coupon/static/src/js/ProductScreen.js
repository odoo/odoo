odoo.define('pos_coupon.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen');
    const PromoCodeButton = require('pos_coupon.PromoCodeButton');
    const ResetProgramsButton = require('pos_coupon.ResetProgramsButton');
    const ActivePrograms = require('pos_coupon.ActivePrograms');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');
    const { patch } = require('web.utils');

    patch(ProductScreen.prototype, 'pos_coupon', {
        setup() {
            useBarcodeReader(this.env.model.barcodeReader, {
                cashier: async (code) => {
                    await this.env.model.actionHandler({
                        name: 'actionActivateCode',
                        args: [this.props.activeOrder, code.base_code],
                    });
                },
            });
            this._super(...arguments);
        },
        getOrderlineAdditionalClasses(orderline) {
            return Object.assign(this._super(...arguments), { 'program-reward': orderline.is_program_reward });
        },
    });

    patch(ProductScreen, 'pos_coupon', {
        components: { ...ProductScreen.components, PromoCodeButton, ResetProgramsButton, ActivePrograms },
    });

    return ProductScreen;
});
