odoo.define('l10n_de_pos_cert.ProductScreen', function(require) {
    "use strict";

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');
    const { TaxError } = require('l10n_de_pos_cert.errors');

    const _super_productscreen = ProductScreen.prototype;

    const PosDeProductScreen = ProductScreen => class extends ProductScreen {
        //@Override
        async _clickProduct(event) {
            if (this.env.pos.isCountryGermany()) {
                _super_productscreen._clickProduct.apply(this, arguments).catch(async (error) => {
                    if (error instanceof TaxError) {
                        await this._showTaxError()
                    } else {
                        return Promise.reject(error);
                    }
                });
            } else {
                _super_productscreen._clickProduct.apply(this, arguments)
            }
        }
        //@Override
        _barcodeProductAction(code) {
            if (this.env.pos.isCountryGermany()) {
                try {
                    _super_productscreen._barcodeProductAction.apply(this, arguments);
                } catch(error) {
                    if (error instanceof TaxError) {
                        this._showTaxError()
                    } else {
                        throw error;
                    }
                }
            } else {
                _super_productscreen._barcodeProductAction.apply(this, arguments);
            }
        }
        async _showTaxError() {
            const title = this.env._t('Tax error');
            const body = this.env._t(
                'Product has an invalid tax amount. Only standard (16% or 19%), reduced (5% or 7%) and zero (0%) rates are allowed.'
            );
            await this.showPopup('ErrorPopup', { title, body });
        }

    }

    Registries.Component.extend(ProductScreen, PosDeProductScreen);

    return PosDeProductScreen;
});

