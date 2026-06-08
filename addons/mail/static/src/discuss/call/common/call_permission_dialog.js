import { Component, props, signal, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { PermissionPromptDialog } from "@web/core/permission_prompt_dialog/permission_prompt_dialog";
import { useService } from "@web/core/utils/hooks";

export class CallPermissionDialog extends Component {
    static components = { PermissionPromptDialog };
    static template = "discuss.CallPermissionDialog";

    setup() {
        this.props = props({
            close: t.function([]),
            media: t.selection(["camera", "microphone"]),
            permissionPrompt: t.string().optional(),
            suggestAllMedias: t.boolean().optional(true),
            useCamera: t.function([]),
            useMicrophone: t.function([]),
        });
        /** @type {import("@odoo/owl").Signal<Element>} */
        this.rootRef = signal();
        this.rtc = useService("discuss.rtc");
        this.ui = useService("ui");
    }

    async onClickUseMicrophone() {
        if (await this.rtc.askForBrowserPermission({ audio: true }, { rootRef: this.rootRef })) {
            await this.props.useMicrophone();
        }
        this.props.close();
    }

    async onClickUseCamera() {
        if (await this.rtc.askForBrowserPermission({ video: true }, { rootRef: this.rootRef })) {
            await this.props.useCamera();
        }
        this.props.close();
    }

    async onClickUseMicAndCamera() {
        if (
            await this.rtc.askForBrowserPermission(
                { audio: true, video: true },
                { rootRef: this.rootRef }
            )
        ) {
            await Promise.all([this.props.useMicrophone(), this.props.useCamera()]);
        }
        this.props.close();
    }

    get secondaryActionText() {
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
