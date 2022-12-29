/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

export class UserSettings {
    id;

    constructor(env, services) {
        this.orm = services.orm;
        this.user = services.user;
        this.hasCanvasFilterSupport =
            typeof document.createElement("canvas").getContext("2d").filter !== "undefined";
    }
    /**
     * @param {Object} settings: the old model-style command with the settings from the server
     *
     * Parses the settings commands and updates the user settings accordingly.
     */
    updateFromCommands(settings) {
        this.usePushToTalk = settings.use_push_to_talk ?? this.usePushToTalk;
        this.pushToTalkKey = settings.push_to_talk_key ?? this.pushToTalkKey;
        this.voiceActiveDuration = settings.voice_active_duration ?? this.voiceActiveDuration;
        //process volume settings model command
        if (!settings.volume_settings_ids) {
            return;
        }
        const volumeRecordSet = settings.volume_settings_ids?.[0][1] ?? [];
        for (const volumeRecord of volumeRecordSet) {
            this.partnerVolumes.set(volumeRecord.partner_id.id, volumeRecord.volume);
        }
    }
    // lookups at partner.volumeSetting.volume should now be settings.partnerVolumes.get(partnerId)
    partnerVolumes = new Map();
    /**
     * DeviceId of the audio input selected by the user
     */
    audioInputDeviceId = "";
    backgroundBlurAmount = 10;
    edgeBlurAmount = 10;
    /**
     * true if listening to keyboard input to register the push to talk key.
     */
    isRegisteringKey = false;
    logRtc = false;
    pushToTalkKey;
    usePushToTalk = false;
    voiceActiveDuration = 0;
    useBlur = false;
    volumeSettingsTimeouts = new Map();
    /**
     * Normalized [0, 1] volume at which the voice activation system must consider the user as "talking".
     */
    voiceActivationThreshold = 0.05;
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

    // "setters"

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
        this.voiceActiveDuration = parseInt(value, 10);
        this._saveSettings();
    }
    /**
     * @param {event} ev
     */
    async setPushToTalkKey(ev) {
        const pushToTalkKey = `${ev.shiftKey || ""}.${ev.ctrlKey || ev.metaKey || ""}.${
            ev.altKey || ""
        }.${ev.key === " " ? "Space" : ev.key}`;
        this.pushToTalkKey = pushToTalkKey;
        this._saveSettings();
    }
    /**
     * @param {Object} param0
     * @param {number} [param0.partnerId]
     * @param {number} param0.volume
     */
    async saveVolumeSetting({ partnerId, volume }) {
        const key = `${partnerId}`;
        if (this.volumeSettingsTimeouts.get(key)) {
            browser.clearTimeout(this.volumeSettingsTimeouts.get(key));
        }
        this.volumeSettingsTimeouts.set(
            key,
            browser.setTimeout(
                this._onSaveVolumeSettingTimeout.bind(this, { key, partnerId, volume }),
                5000
            )
        );
    }
    /**
     * @param {float} voiceActivationThreshold
     */
    setThresholdValue(voiceActivationThreshold) {
        this.voiceActivationThreshold = voiceActivationThreshold;
        browser.localStorage.setItem(
            "mail_user_setting_voice_threshold",
            voiceActivationThreshold.toString()
        );
    }

    // methods

    /**
     * @param {event} ev
     * @param {Object} param1
     * @param {boolean} param1.ignoreModifiers
     */
    isPushToTalkKey(ev, { ignoreModifiers = false } = {}) {
        if (!this.usePushToTalk || !this.pushToTalkKey) {
            return false;
        }
        const { key, shiftKey, ctrlKey, altKey } = this.pushToTalkKeyFormat();
        if (ignoreModifiers) {
            return ev.key === key;
        }
        return (
            ev.key === key &&
            ev.shiftKey === shiftKey &&
            ev.ctrlKey === ctrlKey &&
            ev.altKey === altKey
        );
    }
    pushToTalkKeyFormat() {
        if (!this.pushToTalkKey) {
            return;
        }
        const [shiftKey, ctrlKey, altKey, key] = this.pushToTalkKey.split(".");
        return {
            shiftKey: !!shiftKey,
            ctrlKey: !!ctrlKey,
            altKey: !!altKey,
            key: key || false,
        };
    }
    togglePushToTalk() {
        this.usePushToTalk = !this.usePushToTalk;
        this._saveSettings();
    }
    /**
     * @private
     */
    _loadLocalSettings() {
        const voiceActivationThresholdString = browser.localStorage.getItem(
            "mail_user_setting_voice_threshold"
        );
        const audioInputDeviceId = browser.localStorage.getItem(
            "mail_user_setting_audio_input_device_id"
        );
        this.voiceActivationThreshold = voiceActivationThresholdString
            ? parseFloat(voiceActivationThresholdString)
            : undefined;
        this.audioInputDeviceId = audioInputDeviceId || undefined;
    }
    /**
     * @private
     * @param {Event} ev
     *
     * Syncs the setting across tabs.
     */
    _onStorage(ev) {
        if (ev.key === "mail_user_setting_voice_threshold") {
            this.voiceActivationThreshold = ev.newValue;
        }
    }
    /**
     * @private
     */
    async _onSaveGlobalSettingsTimeout() {
        this.globalSettingsTimeout = undefined;
        await this.orm.call("res.users.settings", "set_res_users_settings", [[this.id]], {
            new_settings: {
                push_to_talk_key: this.pushToTalkKey,
                use_push_to_talk: this.usePushToTalk,
                voice_active_duration: this.voiceActiveDuration,
            },
        });
    }
    /**
     * @param {Object} param0
     * @param {String} param0.key
     * @param {number} [param0.partnerId]
     * @param {number} param0.volume
     */
    async _onSaveVolumeSettingTimeout({ key, partnerId, guestId, volume }) {
        this.volumeSettingsTimeouts.delete(key);
        await this.orm.call("res.users.settings", "set_volume_setting", [[this.id]], {
            partner_id: partnerId,
            volume,
            guest_id: guestId,
        });
    }
    /**
     * @private
     */
    async _saveSettings() {
        // return if guest, formerly !messaging.currentUser, could check user service at some point when guests are supported
        browser.clearTimeout(this.globalSettingsTimeout);
        this.globalSettingsTimeout = browser.setTimeout(
            () => this._onSaveGlobalSettingsTimeout(),
            2000
        );
    }
}

export const userSettingsService = {
    dependencies: ["orm", "user"],
    start(env, services) {
        return new UserSettings(env, services);
    },
};

registry.category("services").add("mail.user_settings", userSettingsService);
