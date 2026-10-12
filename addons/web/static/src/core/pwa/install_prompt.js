import { Component, t, useProps } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { isIOS } from "@web/core/browser/feature_detection";

export class InstallPrompt extends Component {
    props = useProps({
        close: t.any(),
        onClose: t.function(),
    });
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
