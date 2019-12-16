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
     * When the user joins the course, if it's set as "on payment":
     * - If the user is logged in, we redirect to the shop page for this course
     * - If the user is public, we create a login URL that redirects to the shop page afterwards.
     *
     * @param {MouseEvent} ev
     * @override
     * @private
     */
    _onClickJoin: function (ev) {
        this._super.apply(this, arguments);

        if (this.channel.channelEnroll === 'payment') {
            var shopUrl = _.str.sprintf('/shop/cart/update?product_id=%s&amp;express=1', this.productId);
            if (this.publicUser) {
                shopUrl = _.str.sprintf('/web/login?redirect=%s', encodeURIComponent(shopUrl));
            }
            this.beforeJoin().then(function () {
                window.location.href = shopUrl;
            });
        }
    },
});

return CourseJoinWidget;

});
