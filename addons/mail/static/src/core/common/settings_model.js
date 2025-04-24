import { hasHardwareAcceleration } from "@mail/utils/common/misc";
import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { fields, Record } from "./record";
import { debounce } from "@web/core/utils/timing";
import { rpc } from "@web/core/network/rpc";

const MESSAGE_SOUND = "mail.user_setting.message_sound";

export class Settings extends Record {
    id;

    static new() {
        const record = super.new(...arguments);
        record.onStorage = record.onStorage.bind(record);
        browser.addEventListener("storage", record.onStorage);
        return record;
    }

    setup() {
        super.setup();
        this.saveVoiceThresholdDebounce = debounce(() => {
            browser.localStorage.setItem(
                "mail_user_setting_voice_threshold",
                this.voiceActivationThreshold.toString()
            );
        }, 2000);
        this.hasCanvasFilterSupport =
            typeof document.createElement("canvas").getContext("2d").filter !== "undefined";
        this._loadLocalSettings();
    }

    delete() {
        browser.removeEventListener("storage", this.onStorage);
        super.delete(...arguments);
    }

    // Notification settings
    /**
     * @type {"mentions"|"all"|"no_notif"}
     */
    channel_notifications = fields.Attr("mentions", {
        compute() {
            return this.channel_notifications === false ? "mentions" : this.channel_notifications;
        },
    });
    messageSound = fields.Attr(true, {
        compute() {
            return browser.localStorage.getItem(MESSAGE_SOUND) !== "false";
        },
        /** @this {import("models").Settings} */
        onUpdate() {
            if (this.messageSound) {
                browser.localStorage.removeItem(MESSAGE_SOUND);
            } else {
                browser.localStorage.setItem(MESSAGE_SOUND, "false");
            }
        },
    });

    // Voice settings
    // DeviceId of the audio input selected by the user
    audioInputDeviceId = "";
    audioOutputDeviceId = "";
    cameraInputDeviceId = "";
    use_push_to_talk = false;
    voice_active_duration = 200;
    volumes = fields.Many("Volume");
    volumeSettingsTimeouts = new Map();
    // Normalized [0, 1] volume at which the voice activation system must consider the user as "talking".
    voiceActivationThreshold = 0.05;
    // true if listening to keyboard input to register the push to talk key.
    isRegisteringKey = false;
    push_to_talk_key;

    // Video settings
    backgroundBlurAmount = 10;
    edgeBlurAmount = 10;
    showOnlyVideo = false;
    useBlur = false;
    blurPerformanceWarning = fields.Attr(false, {
        compute() {
            const rtc = this.store.rtc;
            if (!rtc || !this.useBlur) {
                return false;
            }
            return this.useBlur && rtc.state?.cameraTrack && !hasHardwareAcceleration();
        },
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
            constraints.deviceId = this.audioInputDeviceId;
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
     * @param {String} audioInputDeviceId
     */
    async setAudioInputDevice(audioInputDeviceId) {
        this.audioInputDeviceId = audioInputDeviceId;
        browser.localStorage.setItem("mail_user_setting_audio_input_device_id", audioInputDeviceId);
    }
    /**
     * @param {String} audioOutputDeviceId
     */
    async setAudioOutputDevice(audioOutputDeviceId) {
        this.audioOutputDeviceId = audioOutputDeviceId;
        browser.localStorage.setItem(
            "mail_user_setting_audio_output_device_id",
            audioOutputDeviceId
        );
    }
    /**
     * @param {String} cameraInputDeviceId
     */
    async setCameraInputDevice(cameraInputDeviceId) {
        this.cameraFacingMode = undefined;
        this.cameraInputDeviceId = cameraInputDeviceId;
        browser.localStorage.setItem(
            "mail_user_setting_camera_input_device_id",
            cameraInputDeviceId
        );
    }
    /**
     * @param {string} value
     */
    setDelayValue(value) {
        this.voice_active_duration = parseInt(value, 10);
        this._saveSettings();
    }
    /**
     * @param {event} ev
     */
    async setPushToTalkKey(ev) {
        const nonElligibleKeys = new Set(["Shift", "Control", "Alt", "Meta"]);
        let pushToTalkKey = `${ev.shiftKey || ""}.${ev.ctrlKey || ev.metaKey || ""}.${
            ev.altKey || ""
        }`;
        if (!nonElligibleKeys.has(ev.key)) {
            pushToTalkKey += `.${ev.key === " " ? "Space" : ev.key}`;
        }
        this.push_to_talk_key = pushToTalkKey;
        this._saveSettings();
    }
    /**
     * @param {Object} param0
     * @param {number} [param0.partnerId]
     * @param {number} [param0.guestId]
     * @param {number} param0.volume
     */
    async saveVolumeSetting({ partnerId, guestId, volume }) {
        if (!this.store.self_partner) {
            return;
        }
        const key = `${partnerId}_${guestId}`;
        if (this.volumeSettingsTimeouts.get(key)) {
            browser.clearTimeout(this.volumeSettingsTimeouts.get(key));
        }
        this.volumeSettingsTimeouts.set(
            key,
            browser.setTimeout(
                this._onSaveVolumeSettingTimeout.bind(this, { key, partnerId, guestId, volume }),
                5000
            )
        );
    }
    /**
     * @param {float} voiceActivationThreshold
     */
    setThresholdValue(voiceActivationThreshold) {
        this.voiceActivationThreshold = voiceActivationThreshold;
        this.saveVoiceThresholdDebounce();
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
        if (!this.use_push_to_talk || !this.push_to_talk_key) {
            return false;
        }
        const [shiftKey, ctrlKey, altKey, key] = this.push_to_talk_key.split(".");
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
    pushToTalkKeyFormat() {
        if (!this.push_to_talk_key) {
            return;
        }
        const [shiftKey, ctrlKey, altKey, key] = this.push_to_talk_key.split(".");
        return {
            shiftKey: !!shiftKey,
            ctrlKey: !!ctrlKey,
            altKey: !!altKey,
            key: key || false,
        };
    }
    setPushToTalk(value) {
        this.use_push_to_talk = value;
        this._saveSettings();
    }
    /**
     * @private
     */
    _loadLocalSettings() {
        const voiceActivationThresholdString = browser.localStorage.getItem(
            "mail_user_setting_voice_threshold"
        );
        this.voiceActivationThreshold = voiceActivationThresholdString
            ? parseFloat(voiceActivationThresholdString)
            : this.voiceActivationThreshold;
        this.audioInputDeviceId = browser.localStorage.getItem(
            "mail_user_setting_audio_input_device_id"
        );
        this.audioOutputDeviceId = browser.localStorage.getItem(
            "mail_user_setting_audio_output_device_id"
        );
        this.cameraInputDeviceId = browser.localStorage.getItem(
            "mail_user_setting_camera_input_device_id"
        );
        this.showOnlyVideo =
            browser.localStorage.getItem("mail_user_setting_show_only_video") === "true";
        this.useBlur = browser.localStorage.getItem("mail_user_setting_use_blur") === "true";
        const backgroundBlurAmount = browser.localStorage.getItem(
            "mail_user_setting_background_blur_amount"
        );
        this.backgroundBlurAmount = backgroundBlurAmount ? parseInt(backgroundBlurAmount) : 10;
        const edgeBlurAmount = browser.localStorage.getItem("mail_user_setting_edge_blur_amount");
        this.edgeBlurAmount = edgeBlurAmount ? parseInt(edgeBlurAmount) : 10;
    }
    /**
     * @private
     */
    async _onSaveGlobalSettingsTimeout() {
        this.globalSettingsTimeout = undefined;
        await this.store.env.services.orm.call(
            "res.users.settings",
            "set_res_users_settings",
            [[this.id]],
            {
                new_settings: {
                    push_to_talk_key: this.push_to_talk_key,
                    use_push_to_talk: this.use_push_to_talk,
                    voice_active_duration: this.voice_active_duration,
                },
            }
        );
    }
    /**
     * @param {Object} param0
     * @param {String} param0.key
     * @param {number} [param0.partnerId]
     * @param {number} param0.volume
     */
    async _onSaveVolumeSettingTimeout({ key, partnerId, guestId, volume }) {
        this.volumeSettingsTimeouts.delete(key);
        await this.store.env.services.orm.call(
            "res.users.settings",
            "set_volume_setting",
            [[this.id], partnerId, volume],
            { guest_id: guestId }
        );
    }
    onStorage(ev) {
        if (ev.key === MESSAGE_SOUND) {
            this.messageSound = ev.newValue !== "false";
        }
    }
    /**
     * @private
     */
    async _saveSettings() {
        if (!this.store.self_partner) {
            return;
        }
        browser.clearTimeout(this.globalSettingsTimeout);
        this.globalSettingsTimeout = browser.setTimeout(
            () => this._onSaveGlobalSettingsTimeout(),
            2000
        );
    }
}

Settings.register();
