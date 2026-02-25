import { _t } from "@web/core/l10n/translation";
import { NotificationAlertDialog } from "@web/core/notification_alert_dialog/notification_alert_dialog";
import { useService } from "@web/core/utils/hooks";

export class CallPermissionDeniedDialog extends NotificationAlertDialog {
    static defaultProps = {
        ...NotificationAlertDialog.defaultProps,
        animateMouse: false,
    };
    static props = [...NotificationAlertDialog.props, "permissionType?"];
    static template = "discuss.CallPermissionDeniedDialog";

    setup() {
        this.ui = useService("ui");
    }

    get title() {
        const permissionType = this.props.permissionType;
        if (permissionType === "camera") {
            return _t("Unable to access your camera");
        }
        if (permissionType === "microphone") {
            return _t("Unable to access your microphone");
        }
        return _t("Unable to access your camera and microphone");
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
