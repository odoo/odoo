/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { browser } from "@web/core/browser/browser";

registerModel({
    name: 'Device',
    identifyingFields: ['messaging'],
    lifecycleHooks: {
        _created() {
            this._refresh();
            this._onResize = _.debounce(() => this._refresh(), 100);
        },
        _willDelete() {
            browser.removeEventListener('resize', this._onResize);
        },
    },
    recordMethods: {
        /**
         * Called when messaging is started.
         */
        start() {
            browser.addEventListener('resize', this._onResize);
        },
        /**
         * @private
         */
        _refresh() {
            this.update({
                globalWindowInnerHeight: this.messaging.browser.innerHeight,
                globalWindowInnerWidth: this.messaging.browser.innerWidth,
                isMobile: this.env.device.isMobile,
                isMobileDevice: this.env.device.isMobileDevice,
                sizeClass: this.env.device.size_class,
            });
        },
    },
    fields: {
        globalWindowInnerHeight: attr(),
        globalWindowInnerWidth: attr(),
        /**
         * States whether this device has a small size (note: this field name is not ideal).
         */
        isMobile: attr(),
        /**
         * States whether this device is an actual mobile device.
         */
        isMobileDevice: attr(),
        /**
         * Size class of the device.
         *
         * This is an integer representation of the size.
         * Useful for conditional based on a device size, including
         * lower/higher. Device size classes are defined in sizeClasses
         * attribute.
         */
        sizeClass: attr(),
    },
});
