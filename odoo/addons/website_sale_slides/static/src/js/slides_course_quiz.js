/** @odoo-module **/

import {websiteSlidesQuizNoFullscreen} from "@website_slides/js/slides_course_quiz";

websiteSlidesQuizNoFullscreen.include({
    _extractChannelData: function (slideData) {
        return Object.assign({}, this._super.apply(this, arguments), {
            productId: slideData.productId,
            enroll: slideData.enroll,
            currencyName: slideData.currencyName,
            currencySymbol: slideData.currencySymbol,
            price: slideData.price,
            hasDiscountedPrice: slideData.hasDiscountedPrice
        });
    }
});
