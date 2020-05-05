odoo.define('l10n_fr_pos_cert.ProductScreen', function(require) {

    const ProductScreen = require('point_of_sale.ProductScreen');
    const Registries = require('point_of_sale.Registries');

    const PosFrProductScreen = ProductScreen => class extends ProductScreen {
        disallowLineQuantityChange() {
            let result = super.disallowLineQuantityChange();
            return (this.env.pos.is_french_country() && this.numpadMode === 'quantity') || result;
        }
    };

    Registries.Component.extend(ProductScreen, PosFrProductScreen);

    return ProductScreen;
});
