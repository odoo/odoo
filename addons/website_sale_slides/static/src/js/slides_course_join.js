/** @odoo-module **/

import CourseJoin from "@website_slides/js/slides_course_join";
import wUtils from "@website/js/utils";

const CourseJoinWidget = CourseJoin.courseJoinWidget;

CourseJoinWidget.include({
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
            const self = this;
            this.beforeJoin().then(function () {
                wUtils.sendRequest('/shop/cart/update', {
                    product_id: self.productId,
                    express: 1,
                });
            });
        } else {
            this._super.apply(this, arguments);
        }
    },
});

export default CourseJoinWidget;
