/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class GiftCardButton extends PosComponent {
    setup() {
        super.setup()
        useListener('click', this.onClick);
    }

    async onClick() {
        this.showPopup('GiftCardPopup', {});
    }
}

GiftCardButton.template = 'GiftCardButton';

ProductScreen.addControlButton({
    component: GiftCardButton,
    condition: function () {
        return this.env.pos.config.use_gift_card;
    },
});

Registries.Component.add(GiftCardButton);
