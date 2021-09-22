odoo.define('point_of_sale.MobileSaleOrderManagementScreen', function (require) {
    const SaleOrderManagementScreen = require('pos_sale.SaleOrderManagementScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { useState } = owl.hooks;

    const MobileSaleOrderManagementScreen = (SaleOrderManagementScreen) => {
        class MobileSaleOrderManagementScreen extends SaleOrderManagementScreen {
            constructor() {
                super(...arguments);
                useListener('click-order', this._onShowDetails)
                this.mobileState = useState({ showDetails: false });
            }
            _onShowDetails() {
                this.mobileState.showDetails = true;
            }
        }
        MobileSaleOrderManagementScreen.template = 'MobileSaleOrderManagementScreen';
        return MobileSaleOrderManagementScreen;
    };

    Registries.Component.addByExtending(MobileSaleOrderManagementScreen, SaleOrderManagementScreen);

    return MobileSaleOrderManagementScreen;
});
