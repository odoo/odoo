odoo.define('website_sale_slides.quiz', function (require) {
"use strict";

const {websiteSlidesQuizNoFullscreen} = require('@website_slides/js/slides_course_quiz');

websiteSlidesQuizNoFullscreen.include({
    _extractChannelData: function (slideData) {
        return _.extend({}, this._super.apply(this, arguments), {
            productId: slideData.productId,
            enroll: slideData.enroll,
            currencyName: slideData.currencyName,
            currencySymbol: slideData.currencySymbol,
            price: slideData.price,
            hasDiscountedPrice: slideData.hasDiscountedPrice
        });
    }
});
});
