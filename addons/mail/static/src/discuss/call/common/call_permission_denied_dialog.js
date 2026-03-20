import { Component } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class CallPermissionDeniedDialog extends Component {
    static template = "discuss.CallPermissionDeniedDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        permissionType: { type: String, optional: true },
    };

    setup() {
        this.ui = useService("ui");
    }

    get title() {
        const permissionType = this.props.permissionType;
        if (permissionType === "camera") {
            return _t("Discuss cannot access your camera");
        }
        if (permissionType === "microphone") {
            return _t("Discuss cannot access your microphone");
        }
        return _t("Discuss cannot access your camera and microphone");
    }

    get stepTwoText() {
        const permissionType = this.props.permissionType;
        if (permissionType === "camera") {
            return _t("Turn on the camera permission");
        }
        if (permissionType === "microphone") {
            return _t("Turn on the microphone permission");
        }
        return _t("Turn on the camera and microphone permissions");
    }
}
