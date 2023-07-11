odoo.define('pos_giftcard.tour.PosGiftCardsTourMethods', function (require) {
    'use strict';

    const { createTourMethods } = require('point_of_sale.tour.utils');

    class Do {
        useGiftCard(giftCardCode) {
            return [
                {
                    content: 'open gift card popup',
                    trigger: `.control-button:contains("Gift Card")`,
                },
                {
                    content: 'click the "Use a gift card" button',
                    trigger: `.giftCardPopupConfirmButton:contains("Use a gift card")`,
                },
                {
                    content: 'click the "Use a gift card" button',
                    trigger: `.giftCardPopupInput`,
                    run: `text ${giftCardCode}`,
                },
                {
                    content: 'click the "Use a gift card" button',
                    trigger: '.confirm'
                },
            ];
        }
    }
    return createTourMethods('PosGiftCards', Do);
});
