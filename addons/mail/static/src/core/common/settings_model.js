import { hasHardwareAcceleration } from "@mail/utils/common/misc";
import { _t } from "@web/core/l10n/translation";
import { Record } from "@mail/model/export";
import { rpc } from "@web/core/network/rpc";

export class Settings extends Record {
    static singleton = true;

    setup() {
        super.setup();
        this.onChange(
            () => [this.cameraInputDeviceId],
            function onChangeCameraInputDeviceId() {
                this.cameraFacingMode = undefined;
            },
            { immediate: true }
        );
        this.hasCanvasFilterSupport =
            typeof document.createElement("canvas").getContext("2d").filter !== "undefined";
    }

    messageSound = this.localStorage(true);
    useCallAutoFocus = this.localStorage(true);

    // Voice settings
    // DeviceId of the audio input selected by the user
    audioInputDeviceId = this.localStorage("");
    audioOutputDeviceId = this.localStorage("");
    cameraInputDeviceId = this.localStorage("");
    usePushToTalk = this.localStorage(false);
    voiceActiveDuration = this.localStorage(200);
    // Normalized [0, 1] volume at which the voice activation system must consider the user as "talking".
    voiceActivationThreshold = this.localStorage(0.05);
    // true if listening to keyboard input to register the push to talk key.
    isRegisteringKey = false;
    pushToTalkKey = this.localStorage("");

    // Video settings
    backgroundBlurAmount = this.localStorage(10);
    /**
     * Chosen meeting grid layout, persisted across meetings. Holds every
     * {@link import("@mail/discuss/call/common/call_layout").CallLayout} except "discuss" (which
     * exits fullscreen instead of being persisted).
     *
     * @type {import("@mail/discuss/call/common/call_layout").CallLayout}
     */
    callLayout = this.localStorage("auto");
    edgeBlurAmount = this.localStorage(10);
    showOnlyVideo = this.localStorage(false);
    useBlur = this.localStorage(false);
    /**
     * Manual dismissal of the blur performance warning, until the page
     * reloads. Seeing the warning once is enough.
     */
    blurPerformanceWarningDismissed = false;
    blurPerformanceWarning = this.computed(() => {
        const rtc = this.store.rtc;
        if (!rtc || !this.useBlur || this.blurPerformanceWarningDismissed) {
            return false;
        }
        return Boolean(rtc.cameraTrack && !hasHardwareAcceleration());
    });
    cameraFacingMode = undefined;

    logRtc = false;
    /**
     * @returns {Object} MediaTrackConstraints
     */
    get audioConstraints() {
        const constraints = {
            echoCancellation: true,
            noiseSuppression: true,
        };
        if (this.audioInputDeviceId) {
            // The use of `exact` is at least required to make switching device
            // work while in a VoIP call.
            constraints.deviceId = { exact: this.audioInputDeviceId };
        }
        return constraints;
    }

    get cameraConstraints() {
        const constraints = {
            width: 1280,
        };
        if (this.cameraFacingMode) {
            constraints.facingMode = this.cameraFacingMode;
        } else if (this.cameraInputDeviceId) {
            constraints.deviceId = this.cameraInputDeviceId;
        }
        return constraints;
    }

    get pushToTalkKeyText() {
        if (!this.pushToTalkKey) {
            return "";
        }
        const [shiftKey, ctrlKey, altKey, key] = this.pushToTalkKey.split(".");
        const f = (k, name) => (k ? name : "");
        const keys = [f(ctrlKey, "Ctrl"), f(altKey, "Alt"), f(shiftKey, "Shift"), key].filter(
            Boolean
        );
        return keys.join(" + ");
    }

    get NOTIFICATIONS() {
        return [
            {
                label: "all",
                name: _t("All Messages"),
            },
            {
                label: "mentions",
                name: _t("Mentions Only"),
            },
            {
                label: "no_notif",
                name: _t("Nothing"),
            },
        ];
    }

    get MUTES() {
        return [
            {
                label: "15_mins",
                value: 15,
                name: _t("For 15 minutes"),
            },
            {
                label: "1_hour",
                value: 60,
                name: _t("For 1 hour"),
            },
            {
                label: "3_hours",
                value: 180,
                name: _t("For 3 hours"),
            },
            {
                label: "8_hours",
                value: 480,
                name: _t("For 8 hours"),
            },
            {
                label: "24_hours",
                value: 1440,
                name: _t("For 24 hours"),
            },
            {
                label: "forever",
                value: -1,
                name: _t("Until I turn it back on"),
            },
        ];
    }

    getMuteUntilText(dt) {
        if (dt) {
            return dt.year <= luxon.DateTime.now().year + 2
                ? _t(`Until %s`, dt.toLocaleString(luxon.DateTime.DATETIME_MED))
                : _t("Until I turn it back on");
        }
        return undefined;
    }

    /**
     * @param {string} custom_notifications
     * @param {import("models").Thread} thread
     */
    async setCustomNotifications(custom_notifications, thread = undefined) {
        return rpc("/discuss/settings/custom_notifications", {
            custom_notifications:
                !thread && custom_notifications === "mentions" ? false : custom_notifications,
            channel_id: thread?.id,
        });
    }

    /**
     * @param {integer|false} minutes
     * @param {import("models").Thread} thread
     */
    async setMuteDuration(minutes, thread = undefined) {
        return rpc("/discuss/settings/mute", {
            minutes,
            channel_id: thread?.id,
        });
    }

    /**
     * @param {string} channel_type
     * @param {boolean} is_allowed
     */
    setPushNotifications(channel_type, is_allowed) {
        return rpc("/discuss/settings/push_notifications", {
            channel_type,
            is_allowed,
        });
    }

    /**
     * @param {string} value
     */
    setDelayValue(value) {
        this.voiceActiveDuration = parseInt(value, 10);
    }
    /**
     * @param {event} ev
     */
    setPushToTalkKey(ev) {
        const nonElligibleKeys = new Set(["Shift", "Control", "Alt", "Meta"]);
        let pushToTalkKey = `${ev.shiftKey || ""}.${ev.ctrlKey || ev.metaKey || ""}.${
            ev.altKey || ""
        }`;
        if (!nonElligibleKeys.has(ev.key)) {
            pushToTalkKey += `.${ev.key === " " ? "Space" : ev.key}`;
        }
        this.pushToTalkKey = pushToTalkKey;
    }

    // methods

    buildKeySet({ shiftKey, ctrlKey, altKey, key }) {
        const keys = new Set();
        if (key) {
            keys.add(key === "Meta" ? "Alt" : key);
        }
        if (shiftKey) {
            keys.add("Shift");
        }
        if (ctrlKey) {
            keys.add("Control");
        }
        if (altKey) {
            keys.add("Alt");
        }
        return keys;
    }

    /**
     * @param {event} ev
     * @param {Object} param1
     */
    isPushToTalkKey(ev) {
        if (!this.usePushToTalk || !this.pushToTalkKey) {
            return false;
        }
        const [shiftKey, ctrlKey, altKey, key] = this.pushToTalkKey.split(".");
        const settingsKeySet = this.buildKeySet({ shiftKey, ctrlKey, altKey, key });
        const eventKeySet = this.buildKeySet({
            shiftKey: ev.shiftKey,
            ctrlKey: ev.ctrlKey,
            altKey: ev.altKey,
            key: ev.key,
        });
        if (ev.type === "keydown") {
            return [...settingsKeySet].every((key) => eventKeySet.has(key));
        }
        return settingsKeySet.has(ev.key === "Meta" ? "Alt" : ev.key);
    }
}

Settings.register();
