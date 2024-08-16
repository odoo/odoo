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
        const contentEl = this.el.querySelector('.coupon-message-content');
        const titleEl = this.el.querySelector('.coupon-message-title');
        let message = null;

        if (contentEl) {
            message = contentEl.innerHTML;
            if (titleEl) {
                Object.assign(options, { title: titleEl.innerHTML });
            }
        } else if (titleEl) {
            message = titleEl.innerHTML;
        }

        if (this.el.classList.contains('coupon-info-message')) {
            this.notification.add(message, Object.assign({type: 'success'}, options));
        } else if (this.el.classList.contains('coupon-error-message')) {
            this.notification.add(message, Object.assign({type: 'danger'}, options));
        } else if (this.el.classList.contains('coupon-warning-message')) {
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
