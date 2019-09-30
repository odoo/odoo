odoo.define('website_sale_slides.course.join.widget', function (require) {
"use strict";

var CourseJoinWidget = require('website_slides.course.join.widget').courseJoinWidget;

CourseJoinWidget.include({
    xmlDependencies: (CourseJoinWidget.prototype.xmlDependencies || []).concat(
        ["/website_sale_slides/static/src/xml/channel_management.xml"]
    ),
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.productId = options.channel.productId || false;
    },
    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {MouseEvent} ev
     * @private
     */
    _onClickJoin: function (ev) {
        this._super.apply(this, arguments);
        if (this.channel.channelEnroll === 'payment') {
            var url = _.str.sprintf('/shop/cart/update?product_id=%s&amp;express=1', this.productId);
            if (this.publicUser) {
                url = this._getLoginRedirectUrlSale(url);
            }
            this.beforeJoin().then(function () {
                window.location.href = url; 
            });
        }
    },
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * create the url to where the user will be redirected after he logs in
     *
     * @private
     */
    _getLoginRedirectUrlSale: function (baseShopUrl) {
        return _.str.sprintf('/web/login?redirect=%s', encodeURIComponent(baseShopUrl));
    },
});
});
