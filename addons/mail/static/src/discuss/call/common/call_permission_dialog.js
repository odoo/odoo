import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { PermissionPromptDialog } from "@web/core/permission_prompt_dialog/permission_prompt_dialog";
import { useService } from "@web/core/utils/hooks";

export class CallPermissionDialog extends Component {
    static components = { PermissionPromptDialog };
    static props = {
        close: Function,
        media: {
            type: String,
            validate: (s) => ["camera", "microphone"].includes(s),
        },
        permissionPrompt: {
            type: String,
            optional: true,
        },
        suggestAllMedias: {
            type: Boolean,
            optional: true,
        },
        useMicrophone: Function,
        useCamera: Function,
    };
    static defaultProps = {
        suggestAllMedias: true,
    };
    static template = "discuss.CallPermissionDialog";

    setup() {
        this.rtc = useService("discuss.rtc");
        this.ui = useService("ui");
    }

    async onClickUseMicrophone() {
        if (await this.rtc.askForBrowserPermission({ audio: true })) {
            await this.props.useMicrophone();
        }
        this.props.close();
    }

    async onClickUseCamera() {
        if (await this.rtc.askForBrowserPermission({ video: true })) {
            await this.props.useCamera();
        }
        this.props.close();
    }

    async onClickUseMicAndCamera() {
        if (await this.rtc.askForBrowserPermission({ audio: true, video: true })) {
            await Promise.all([this.props.useMicrophone(), this.props.useCamera()]);
        }
        this.props.close();
    }

    get primaryActionText() {
        return this.props.media === "camera" ? _t("Use Camera") : _t("Use Microphone");
    }

    get permissionPrompt() {
        if (this.props.permissionPrompt) {
            return this.props.permissionPrompt;
        }
        if (this.props.media === "microphone") {
            return _t("Do you want people to hear you in the meeting?");
        }
        return _t("Do you want people to see you in the meeting?");
    }

    get permissionNote() {
        return _t("You can still turn off your %s anytime.", this.props.media);
    }
}
