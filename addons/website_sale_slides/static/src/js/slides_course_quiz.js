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
    ),
    events: _.extend({}, Quiz.prototype.events || {}, {
        'click .o_wslides_js_join_course_sale': '_onClickJoinSale',
    }),
    custom_events: _.extend({}, Quiz.prototype.events || {}, {
        'buy_cours': '_onClickJoinSale',
    }),
    /**
     * @private
     */
    _onClickJoinSale: function(){
        var self = this;
        var values = this._getAnswers()
        if (values.length === this.quiz.questions.length){
            this._alertHide();
            values = {'slide_id': this.slide.id, 'slide_answers':values}
            return this._rpc({
                route:'/slides/slide/quiz/save_slide_answsers',
                params: {
                    'slide_values': values,
                }
            }).then( function (){
                if (self.readonly){
                    var url = self._createLoginRedirectUrl()
                }
                else{
                    var url =_.str.sprintf('/shop/cart/update?product_id=%s&amp;express=1',(self.channel.productId));
                    }
                window.location=url
            })

        } else {
            this._alertShow();
        }
    },
    /**
     * @private
     * @param
     */
    _createLoginRedirectUrl: function(){
        var redirectURL= _.str.sprintf('/shop/cart/update?product_id=%s&amp;express=1',(this.channel.productId));
        return _.str.sprintf('/web/login?redirect=%s', encodeURIComponent(redirectURL));
    },
});
});
