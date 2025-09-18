// @ts-check

/** @module @web/services/pwa/install_prompt - Dialog showing Safari-specific PWA installation instructions (iOS and macOS) */

import { Component } from "@odoo/owl";
import { isIOS } from "@web/core/browser/feature_detection";
import { Dialog } from "@web/ui/dialog/dialog";

/**
 * @typedef {Object} InstallPromptProps
 * @property {() => void} close - close the dialog
 * @property {() => void} onClose - callback after close
 */

/**
 * Dialog component showing Safari-specific PWA installation instructions.
 * Displays different instructions for iOS (mobile Safari) vs macOS Safari.
 */
export class InstallPrompt extends Component {
    static props = {
        close: true,
        onClose: { type: Function },
    };
    static components = {
        Dialog,
    };
    static template = "web.InstallPrompt";

    /** @returns {boolean} whether the device is running iOS (mobile Safari) */
    get isMobileSafari() {
        return isIOS();
    }

    /** Close the dialog and invoke the onClose callback. */
    onClose() {
        this.props.close();
        this.props.onClose();
    }
}
