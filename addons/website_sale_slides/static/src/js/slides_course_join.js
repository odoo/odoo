odoo.define('website_sale_slides.course.join.widget', function (require) {
"use strict";

var CourseJoinWidget = require('website_slides.course.join.widget').courseJoinWidget;
const wUtils = require('website.utils');

CourseJoinWidget.include({
    xmlDependencies: (CourseJoinWidget.prototype.xmlDependencies || []).concat(
        ["/website_sale_slides/static/src/xml/slide_course_join.xml"]
    ),
    init: function (parent, options) {
        this._super.apply(this, arguments);
        this.productId = options.channel.productId || false;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * When the user joins the course, if it's set as "on payment" and the user is logged in,
     * we redirect to the shop page for this course.
     *
     * @param {MouseEvent} ev
     * @override
     * @private
     */
    _onClickJoin: function (ev) {
        ev.preventDefault();

        if (this.channel.channelEnroll === 'payment' && !this.publicUser) {
            this.beforeJoin().then(function () {
                wUtils.sendRequest('/shop/cart/update', {
                    product_id: this.productId,
                    express: 1,
                });
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
});

return CourseJoinWidget;

});
