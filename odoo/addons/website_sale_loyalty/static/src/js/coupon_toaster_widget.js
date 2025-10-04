/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import {registry} from "@web/core/registry";

const CouponToasterWidget = publicWidget.Widget.extend({
    init() {
        this._super(...arguments);
        this.notification = this.bindService("notification");
    },

    start() {
        let options = {};
        const $content = this.$('.coupon-message-content');
        const $title = this.$('.coupon-message-title');
        let message = null;

        if ($content.length) {
            message = $content[0].innerHTML;
            if ($title.length) {
                Object.assign(options, {title: $title[0].innerHTML});
            }
        } else if ($title.length) {
            message = $title[0].innerHTML;
        }

        if (this.$el.hasClass('coupon-info-message')) {
            this.notification.add(message, Object.assign({type: 'success'}, options));
        } else if (this.$el.hasClass('coupon-error-message')) {
            this.notification.add(message, Object.assign({type: 'danger'}, options));
        } else if (this.$el.hasClass('coupon-warning-message')) {
            this.notification.add(message, Object.assign({type: 'warning'}, options));
        }

        return this._super(...arguments);
    },
});

registry.category("public_root_widgets").add("CouponToasterWidget", {
    Widget: CouponToasterWidget,
    selector: '.coupon-message',
});

export default CouponToasterWidget;
