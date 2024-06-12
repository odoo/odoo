/* @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";

export class UserSettings {
    id;

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    constructor(env, services) {
        this.orm = services.orm;
        this.store = services["mail.store"];
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
        this.setVolumes(volumeRecordSet);
    }
    partnerVolumes = new Map();
    guestVolumes = new Map();
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
    voiceActiveDuration = 200;
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

    getVolume(rtcSession) {
        return (
            rtcSession.volume ||
            this.partnerVolumes.get(rtcSession.partnerId) ||
            this.guestVolumes.get(rtcSession.guestId) ||
            0.5
        );
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

    setVolumes(volumeRecordSet) {
        for (const volumeRecord of volumeRecordSet) {
            if (volumeRecord.partner_id) {
                this.partnerVolumes.set(volumeRecord.partner_id.id, volumeRecord.volume);
            } else if (volumeRecord.guest_id) {
                this.guestVolumes.set(volumeRecord.guest_id.id, volumeRecord.volume);
            }
        }
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
        this.pushToTalkKey = pushToTalkKey;
        this._saveSettings();
    }
    /**
     * @param {Object} param0
     * @param {number} [param0.partnerId]
     * @param {number} [param0.guestId]
     * @param {number} param0.volume
     */
    async saveVolumeSetting({ partnerId, guestId, volume }) {
        if (this.store.self?.type === "guest") {
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
        this.voiceActivationThreshold = voiceActivationThresholdString
            ? parseFloat(voiceActivationThresholdString)
            : this.voiceActivationThreshold;
        this.audioInputDeviceId = browser.localStorage.getItem(
            "mail_user_setting_audio_input_device_id"
        );
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
        await this.orm.call(
            "res.users.settings",
            "set_volume_setting",
            [[this.id], partnerId, volume],
            {
                guest_id: guestId,
            }
        );
    }
    /**
     * @private
     */
    async _saveSettings() {
        if (this.store.self?.type === "guest") {
            return;
        }
        browser.clearTimeout(this.globalSettingsTimeout);
        this.globalSettingsTimeout = browser.setTimeout(
            () => this._onSaveGlobalSettingsTimeout(),
            2000
        );
    }
}

export const userSettingsService = {
    dependencies: ["orm", "mail.store"],
    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Partial<import("services").Services>} services
     */
    start(env, services) {
        return new UserSettings(env, services);
    },
};

registry.category("services").add("mail.user_settings", userSettingsService);
