/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { SIZES } from '@web/core/ui/ui_service';

registerModel({
    name: 'Device',
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
         * @returns {boolean}
         */
        _computeHasRtcSupport() {
            return Boolean(window.RTCPeerConnection && window.MediaStream);
        },
        /**
         * @private
         */
        _refresh() {
            this.update({
                globalWindowInnerHeight: this.messaging.browser.innerHeight,
                globalWindowInnerWidth: this.messaging.browser.innerWidth,
                isMobileDevice: isMobileOS(),
                isSmall: this.env.isSmall,
                sizeClass: this.env.services.ui.size,
            });
        },
    },
    fields: {
        globalWindowInnerHeight: attr(),
        globalWindowInnerWidth: attr(),
        hasRtcSupport: attr({
            compute: '_computeHasRtcSupport',
        }),
        /**
         * States whether this device is an actual mobile device.
         */
        isMobileDevice: attr(),
        /**
         * States whether this device has a small size.
         */
        isSmall: attr(),
        /**
         * Size class of the device.
         *
         * This is an integer representation of the size.
         * Useful for conditional based on a device size, including
         * lower/higher. Device size classes are defined in sizeClasses
         * attribute.
         */
        sizeClass: attr(),
        sizeClasses: attr({
            default: SIZES,
        }),
    },
});
