odoo.define('point_of_sale.ProductInfoPopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    /**
     * Props:
     *  {
     *      info: {object of data}
     *  }
     */
    class ProductInfoPopup extends AbstractAwaitablePopup {
        setup() {
            super.setup();
            Object.assign(this, this.props.info);
        }
        searchProduct(productName) {
            this.env.posbus.trigger('search-product-from-info-popup', productName);
            this.cancel()
        }
        _hasMarginsCostsAccessRights() {
            const isAccessibleToEveryUser = this.env.pos.config.is_margins_costs_accessible_to_every_user;
            const isCashierManager = this.env.pos.get_cashier().role === 'manager';
            return isAccessibleToEveryUser || isCashierManager;
        }
    }

    ProductInfoPopup.template = 'ProductInfoPopup';
    ProductInfoPopup.defaultProps= { confirmKey: false };
    Registries.Component.add(ProductInfoPopup);
});
