/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { isIOS } from "@web/core/browser/feature_detection";

export class InstallPrompt extends Component {
    static props = {
        close: true,
        onClose: { type: Function },
    };
    static components = {
        Dialog,
    };
    static template = "web.InstallPrompt";

    get isMobileSafari() {
        return isIOS();
    }

    onClose() {
        this.props.close();
        this.props.onClose();
    }
}
