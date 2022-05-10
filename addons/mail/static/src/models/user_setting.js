/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr, many, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'UserSetting',
    identifyingFields: ['id'],
    lifecycleHooks: {
        _created() {
            this._loadLocalSettings();
            browser.addEventListener('storage', this._onStorage);
        },
        _willDelete() {
            browser.removeEventListener('storage', this._onStorage);
            for (const timeout of Object.values(this.volumeSettingsTimeouts)) {
                this.messaging.browser.clearTimeout(timeout);
            }
            this.messaging.browser.clearTimeout(this.globalSettingsTimeout);
        },
    },
    modelMethods: {
        /**
         * @param {Object} data
         * @returns {Object}
         */
        convertData(data) {
            const data2 = {};
            if ('use_push_to_talk' in data) {
                data2.usePushToTalk = data.use_push_to_talk;
            }
            if ('push_to_talk_key' in data) {
                data2.pushToTalkKey = data.push_to_talk_key || '';
            }
            if ('voice_active_duration' in data) {
                data2.voiceActiveDuration = data.voice_active_duration;
            }
            if ('id' in data) {
                data2.id = data.id;
            }
            return data2;
        },
    },
    recordMethods: {
        /**
         * @returns {Object} MediaTrackConstraints
         */
        getAudioConstraints() {
            const constraints = {
                echoCancellation: true,
                noiseSuppression: true,
            };
            if (this.audioInputDeviceId) {
                constraints.deviceId = this.audioInputDeviceId;
            }
            return constraints;
        },
        /**
         * @param {event} ev
         * @param {Object} param1
         * @param {boolean} param1.ignoreModifiers
         */
        isPushToTalkKey(ev, { ignoreModifiers = false } = {}) {
            if (!this.usePushToTalk || !this.pushToTalkKey) {
                return;
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
        },
        pushToTalkKeyFormat() {
            if (!this.pushToTalkKey) {
                return;
            }
            const [shiftKey, ctrlKey, altKey, key] = this.pushToTalkKey.split('.');
            return {
                shiftKey: !!shiftKey,
                ctrlKey: !!ctrlKey,
                altKey: !!altKey,
                key: key || false,
            };
        },
        pushToTalkKeyToString() {
            const { shiftKey, ctrlKey, altKey, key } = this.pushToTalkKeyFormat();
            const f = (k, name) => k ? name : '';
            return `${f(ctrlKey, 'Ctrl + ')}${f(altKey, 'Alt + ')}${f(shiftKey, 'Shift + ')}${key}`;
        },
        /**
         * @param {String} audioInputDeviceId
         */
        async setAudioInputDevice(audioInputDeviceId) {
            this.update({
                audioInputDeviceId,
            });
            browser.localStorage.setItem('mail_user_setting_audio_input_device_id', audioInputDeviceId);
            await this.messaging.rtc.updateLocalAudioTrack(true);
        },
        /**
         * @param {String} value
         */
        setDelayValue(value) {
            const voiceActiveDuration = parseInt(value, 10);
            this.update({ voiceActiveDuration });
            if (!this.messaging.isCurrentUserGuest) {
                this._saveSettings();
            }
        },
        /**
         * @param {event} ev
         */
        async setPushToTalkKey(ev) {
            const pushToTalkKey = `${ev.shiftKey || ''}.${ev.ctrlKey || ev.metaKey || ''}.${ev.altKey || ''}.${ev.key}`;
            this.update({ pushToTalkKey });
            if (!this.messaging.isCurrentUserGuest) {
                this._saveSettings();
            }
        },
        /**
         * @param {Object} param0
         * @param {number} [param0.guestId]
         * @param {number} [param0.partnerId]
         * @param {number} param0.volume
         */
        async saveVolumeSetting({ guestId, partnerId, volume }) {
            if (this.volumeSettingsTimeouts[partnerId]) {
                this.messaging.browser.clearTimeout(this.volumeSettingsTimeouts[partnerId]);
            }
            this.update({
                volumeSettingsTimeouts: {
                    ...this.volumeSettingsTimeouts,
                    [partnerId]: this.messaging.browser.setTimeout(
                        this._onSaveVolumeSettingTimeout.bind(this, { guestId, partnerId, volume }),
                        5000,
                    ),
                },
            });
        },
        /**
         * @param {float} voiceActivationThreshold
         */
        async setThresholdValue(voiceActivationThreshold) {
            this.update({ voiceActivationThreshold });
            browser.localStorage.setItem('mail_user_setting_voice_threshold', voiceActivationThreshold.toString());
            await this.messaging.rtc.updateVoiceActivation();
        },
        async togglePushToTalk() {
            this.update({ usePushToTalk: !this.usePushToTalk });
            await this.messaging.rtc.updateVoiceActivation();
            if (!this.messaging.isCurrentUserGuest) {
                this._saveSettings();
            }
        },
        /**
         * toggles the display of the option window
         */
        toggleWindow() {
            this.update({ isOpen: !this.isOpen });
        },
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
            this.update({
                voiceActivationThreshold: voiceActivationThresholdString ? parseFloat(voiceActivationThresholdString) : undefined,
                audioInputDeviceId: audioInputDeviceId || undefined,
            });
        },
        /**
         * @private
         * @param {Event} ev
         */
        async _onStorage(ev) {
            if (ev.key === 'mail_user_setting_voice_threshold') {
                this.update({ voiceActivationThreshold: ev.newValue });
                await this.messaging.rtc.updateVoiceActivation();
            }
        },
        /**
         * @private
         */
        async _onSaveGlobalSettingsTimeout() {
            if (!this.exists()) {
                return;
            }
            this.update({ globalSettingsTimeout: clear() });
            await this.messaging.rpc(
                {
                    model: 'res.users.settings',
                    method: 'set_res_users_settings',
                    args: [[this.messaging.currentUser.resUsersSettingsId], {
                        push_to_talk_key: this.pushToTalkKey,
                        use_push_to_talk: this.usePushToTalk,
                        voice_active_duration: this.voiceActiveDuration,
                    }],
                },
                { shadow: true },
            );
        },
        /**
         * @param {Object} param0
         * @param {number} [param0.guestId]
         * @param {number} [param0.partnerId]
         * @param {number} param0.volume
         */
        async _onSaveVolumeSettingTimeout({ guestId, partnerId, volume }) {
            if (!this.exists()) {
                return;
            }
            const newVolumeSettingsTimeouts = { ...this.volumeSettingsTimeouts };
            delete newVolumeSettingsTimeouts[partnerId];
            this.update({ volumeSettingsTimeouts: newVolumeSettingsTimeouts });
            await this.messaging.rpc(
                {
                    model: 'res.users.settings',
                    method: 'set_volume_setting',
                    args: [
                        [this.messaging.currentUser.resUsersSettingsId],
                        partnerId,
                        volume,
                    ],
                    kwargs: {
                        guest_id: guestId,
                    },
                },
                { shadow: true },
            );
        },
        /**
         * @private
         */
        async _saveSettings() {
            this.messaging.browser.clearTimeout(this.globalSettingsTimeout);
            this.update({
                globalSettingsTimeout: this.messaging.browser.setTimeout(
                    this._onSaveGlobalSettingsTimeout,
                    2000,
                ),
            });
        },
    },
    fields: {
        /**
         * DeviceId of the audio input selected by the user
         */
        audioInputDeviceId: attr({
            default: '',
        }),
        globalSettingsTimeout: attr(),
        id: attr({
            readonly: true,
            required: true,
        }),
        /**
         * Formatted string that represent the push to talk key with its modifiers.
         */
        pushToTalkKey: attr({
            default: '',
        }),
        /**
         * Model for the component with the controls for RTC related settings.
         */
        rtcConfigurationMenu: one('RtcConfigurationMenu', {
            default: insertAndReplace(),
            inverse: 'userSetting',
            isCausal: true,
        }),
        /**
         * layout of the rtc session display chosen by the user
         * possible values: tiled, spotlight, sidebar
         */
        rtcLayout: attr({
            default: 'tiled',
        }),
        /**
         * true if the user wants to use push to talk (over voice activation)
         */
        usePushToTalk: attr({
            default: false,
        }),
        /**
         * Normalized volume at which the voice activation system must consider the user as "talking".
         */
        voiceActivationThreshold: attr({
            default: 0.05,
        }),
        /**
         * how long the voice remains active after releasing the push-to-talk key in ms
         */
        voiceActiveDuration: attr({
            default: 0,
        }),
        /**
         * Determines the volume chosen by the current user for each other user.
         */
        volumeSettings: many('VolumeSetting', {
            inverse: 'userSetting',
            isCausal: true,
        }),
        volumeSettingsTimeouts: attr({
            default: {},
        }),
    },
});
