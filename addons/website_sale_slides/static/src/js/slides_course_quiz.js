odoo.define('website_sale_slides.quiz', function (require) {
"use strict";

var sAnimations = require('website.content.snippets.animation');
var Quiz = require('website_slides.quiz');

sAnimations.registry.websiteSlidesQuizNoFullscreen.include({
    _extractChannelData: function (slideData){
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

Quiz.include({
    xmlDependencies: (Quiz.prototype.xmlDependencies || []).concat(
        ["/website_sale_slides/static/src/xml/website_sale_slides_quiz.xml"]
    )
});
});
