odoo.define('point_of_sale.MobileOrderManagementScreen', function (require) {
    const OrderManagementScreen = require('point_of_sale.OrderManagementScreen');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    const { useState } = owl.hooks;

    const MobileOrderManagementScreen = (OrderManagementScreen) => {
        class MobileOrderManagementScreen extends OrderManagementScreen {
            constructor() {
                super(...arguments);
                useListener('click-order', this._onShowDetails)
                this.mobileState = useState({ showDetails: false });
            }
            _onShowDetails() {
                this.mobileState.showDetails = true;
            }
        }
        MobileOrderManagementScreen.template = 'MobileOrderManagementScreen';
        return MobileOrderManagementScreen;
    };

    Registries.Component.addByExtending(MobileOrderManagementScreen, OrderManagementScreen);

    return MobileOrderManagementScreen;
});
