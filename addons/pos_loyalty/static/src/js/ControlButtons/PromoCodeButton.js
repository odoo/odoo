/** @odoo-module **/

import PosComponent from 'point_of_sale.PosComponent';
import ProductScreen from 'point_of_sale.ProductScreen';
import Registries from 'point_of_sale.Registries';
import { useListener } from "@web/core/utils/hooks";

export class PromoCodeButton extends PosComponent {
    setup() {
        super.setup();
        useListener('click', this.onClick);
    }

    async onClick() {
        let { confirmed, payload: code } = await this.showPopup('TextInputPopup', {
            title: this.env._t('Enter Code'),
            startingValue: '',
            placeholder: this.env._t('Gift card or Discount code'),
        });
        if (confirmed) {
            code = code.trim();
            if (code !== '') {
                this.env.pos.get_order().activateCode(code);
            }
        }
    }
}

PromoCodeButton.template = 'PromoCodeButton';

ProductScreen.addControlButton({
    component: PromoCodeButton,
    condition: function () {
        return this.env.pos.programs.some(p => ['coupon', 'promotion', 'gift_card'].includes(p.program_type));
    }
});

Registries.Component.add(PromoCodeButton);
