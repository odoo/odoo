/** @odoo-module **/

import publicWidget from 'web.public.widget';
import {registry} from "@web/core/registry";

const CouponToasterWidget = publicWidget.Widget.extend({
    start() {
        let options = {};
        const $content = this.$('.coupon-message-content');
        const $title = this.$('.coupon-message-title');

        if ($content.length) {
            Object.assign(options, {message: $content[0].innerHTML});
        }
        if ($title.length) {
            Object.assign(options, {title: $title[0].innerHTML});
        }

        if (this.$el.hasClass('coupon-info-message')) {
            this.displayNotification(Object.assign({type: 'success'}, options));
        } else if (this.$el.hasClass('coupon-error-message')) {
            this.displayNotification(Object.assign({type: 'danger'}, options));
        } else if (this.$el.hasClass('coupon-warning-message')) {
            this.displayNotification(Object.assign({type: 'warning'}, options));
        }

        return this._super(...arguments);
    },
});

registry.category("public_root_widgets").add("CouponToasterWidget", {
    Widget: CouponToasterWidget,
    selector: '.coupon-message',
});

export default CouponToasterWidget;
