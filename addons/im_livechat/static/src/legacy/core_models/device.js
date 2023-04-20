/** @odoo-module **/

import { attr, Model } from "@im_livechat/legacy/model";
import { browser } from "@web/core/browser/browser";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { SIZES } from "@web/core/ui/ui_service";
import { debounce } from "@web/core/utils/timing";

Model({
    name: "Device",
    lifecycleHooks: {
        _created() {
            this._refresh();
            this._onResize = debounce(() => this._refresh(), 100);
        },
        _willDelete() {
            browser.removeEventListener("resize", this._onResize);
        },
    },
    recordMethods: {
        /**
         * Called when messaging is started.
         */
        start() {
            browser.addEventListener("resize", this._onResize);
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
        hasCanvasFilterSupport: attr({
            default:
                typeof document.createElement("canvas").getContext("2d").filter !== "undefined",
        }),
        hasRtcSupport: attr({
            compute() {
                return Boolean(window.RTCPeerConnection && window.MediaStream);
            },
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
        sizeClasses: attr({ default: SIZES }),
    },
});
