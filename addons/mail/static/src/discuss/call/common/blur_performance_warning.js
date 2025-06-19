import { CallPopover } from "@mail/discuss/call/common/call_popover";

import { Component, useState, useEffect } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";
import { memoize } from "@web/core/utils/functions";
import { _t } from "@web/core/l10n/translation";

/**
 * Checks if the browser supports hardware acceleration for video processing.
 *
 * @returns {boolean} True if hardware acceleration is supported, false otherwise.
 */
const checkHardwareAccelerationSupport = memoize(() => {
    const canvas = document.createElement("canvas");
    const gl =
        canvas.getContext("webgl2") ||
        canvas.getContext("webgl") ||
        canvas.getContext("experimental-webgl");
    if (!gl) {
        // WebGL support is typically required for hardware acceleration.
        return false;
    }
    const debugInfo = gl.getExtension("WEBGL_debug_renderer_info");
    if (debugInfo) {
        const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        if (/swiftshader|llvmpipe|software/i.test(renderer)) {
            // These renderers indicate software-based rendering instead of hardware acceleration.
            return false;
        }
    }
    return true;
});

export class BlurPerformanceWarning extends Component {
    static template = "discuss.BlurPerformanceWarning";
    static props = {};
    static components = { CallPopover };

    setup() {
        this.rtc = useService("discuss.rtc");
        this.store = useService("mail.store");
        this.isMobileOS = isMobileOS();
        this.state = useState({
            showWarning: false,
        });
        useEffect(
            () => {
                if (
                    this.store.settings.useBlur &&
                    !this.isMobileOS &&
                    this.rtc.state.cameraTrack &&
                    !checkHardwareAccelerationSupport()
                ) {
                    this.state.showWarning = true;
                } else {
                    this.state.showWarning = false;
                }
            },
            () => [this.store.settings.useBlur, this.rtc.state.cameraTrack]
        );
    }

    onClickClose() {
        this.state.showWarning = false;
    }

    get warningMessage() {
        return {
            title: _t("Performance Warning"),
            body: _t("Hardware acceleration is disabled. This may affect the blur effect."),
        };
    }
}
