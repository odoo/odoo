import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";
import { browser } from "@web/core/browser/browser";
import { Record } from "./record";
import { debounce } from "@web/core/utils/timing";
import { rpc } from "@web/core/network/rpc";

export class Settings extends Record {
    id;

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

    // Notification settings
    /**
     * @type {"mentions"|"all"|"no_notif"}
     */
    channel_notifications = Record.attr("mentions", {
        compute() {
            return this.channel_notifications === false ? "mentions" : this.channel_notifications;
        },
    });
    mute_until_dt = Record.attr(false, { type: "datetime" });

    // Voice settings
    // DeviceId of the audio input selected by the user
    audioInputDeviceId = "";
    use_push_to_talk = false;
    voice_active_duration = 200;
    volumes = Record.many("Volume");
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
                ? sprintf(_t(`Until %s`), dt.toLocaleString(luxon.DateTime.DATETIME_MED))
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
        if (this.store.self.type !== "partner") {
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
    /**
     * @private
     */
    async _saveSettings() {
        if (this.store.self.type !== "partner") {
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
