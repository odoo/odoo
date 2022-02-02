odoo.define('point_of_sale.SetPricelistButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require("@web/core/utils/hooks");
    const Registries = require('point_of_sale.Registries');

    class SetPricelistButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this.onClick);
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get currentPricelistName() {
            const order = this.currentOrder;
            return order && order.pricelist
                ? order.pricelist.display_name
                : this.env._t('Pricelist');
        }
        async onClick() {
            // Create the list to be passed to the SelectionPopup.
            // Pricelist object is passed as item in the list because it
            // is the object that will be returned when the popup is confirmed.
            const selectionList = this.env.pos.pricelists.map(pricelist => ({
                id: pricelist.id,
                label: pricelist.name,
                isSelected: pricelist.id === this.currentOrder.pricelist.id,
                item: pricelist,
            }));

            const { confirmed, payload: selectedPricelist } = await this.showPopup(
                'SelectionPopup',
                {
                    title: this.env._t('Select the pricelist'),
                    list: selectionList,
                }
            );

            if (confirmed) {
                this.currentOrder.set_pricelist(selectedPricelist);
            }
        }
    }
    SetPricelistButton.template = 'SetPricelistButton';

    ProductScreen.addControlButton({
        component: SetPricelistButton,
        condition: function() {
            return this.env.pos.config.use_pricelist && this.env.pos.pricelists.length > 1;
        },
    });

    Registries.Component.add(SetPricelistButton);

    return SetPricelistButton;
});
