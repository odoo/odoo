import { closeStream } from "@mail/utils/common/misc";

import { Component, signal, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { PermissionPromptDialog } from "@web/core/permission_prompt_dialog/permission_prompt_dialog";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export class CallPermissionDialog extends Component {
    static components = { PermissionPromptDialog };
    static template = "discuss.CallPermissionDialog";

    setup() {
        this.props = useProps({
            close: t.function([]),
            media: t.selection(["camera", "microphone"]),
            permissionPrompt: t.string().optional(),
            suggestAllMedias: t.boolean().optional(true),
            useCamera: t.function([], t.promise()),
            useMicrophone: t.function([], t.promise()),
        });
        /** @type {import("@odoo/owl").Signal<Element>} */
        this.rootRef = signal();
        this.singleMediaElementRef = signal.ref(Element);
        this.userMediaElementRef = signal.ref(Element);
        this.rtc = useService("discuss.rtc");
        this.lang = user.lang || document.documentElement.lang || "en-US";
        // Keep <usermedia> mounted if permissions change before its stream event fires.
        this.showUserMediaElement =
            this.rtc.supportsMediaCaptureElement("usermedia") &&
            this.props.suggestAllMedias &&
            this.rtc.cameraPermission !== "granted" &&
            this.rtc.microphonePermission !== "granted";
    }

    async onUserMediaStream() {
        /** @type {MediaStream} */
        const stream = this.userMediaElementRef().stream;
        closeStream(stream);
        this.rtc.microphonePermission = "granted";
        this.rtc.cameraPermission = "granted";
        await Promise.all([this.props.useMicrophone(), this.props.useCamera()]);
        this.props.close();
    }

    async onSingleMediaTrack() {
        const track = this.singleMediaElementRef().track;
        track.stop();
        if (this.props.media === "camera") {
            this.rtc.cameraPermission = "granted";
            await this.props.useCamera();
        } else {
            this.rtc.microphonePermission = "granted";
            await this.props.useMicrophone();
        }
        this.props.close();
    }

    /** @param {Event} event */
    async onMediaCaptureError(event) {
        const elementName = event.currentTarget.localName;
        if (elementName === "usermedia") {
            await this.onClickUseMicAndCamera();
        } else if (elementName === "camera") {
            await this.onClickUseCamera();
        } else {
            await this.onClickUseMicrophone();
        }
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
        return this.props.media === "camera" ? _t("Use camera") : _t("Use microphone");
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
        if (this.props.media === "microphone") {
            return _t("You can still turn off your microphone anytime.");
        }
        return _t("You can still turn off your camera anytime.");
    }
}
