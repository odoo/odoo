/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

/**
 * Models various user settings. It is used as a complement to
 * `res.users.settings`, in order to compute and add data only relevant to the
 * client-side. This is particularly useful for allowing guests to have their
 * own settings.
 */
registerModel({
    name: 'UserSetting',
    lifecycleHooks: {
        _created() {
            this._loadLocalSettings();
            browser.addEventListener('storage', this._onStorage);
        },
        _willDelete() {
            browser.removeEventListener('storage', this._onStorage);
            for (const timeout of Object.values(this.volumeSettingsTimeouts)) {
                this.global.Messaging.browser.clearTimeout(timeout);
            }
            this.global.Messaging.browser.clearTimeout(this.globalSettingsTimeout);
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
            await this.global.Rtc.updateLocalAudioTrack(true);
        },
        /**
         * @param {string} value
         */
        setDelayValue(value) {
            this.update({ localVoiceActiveDuration: parseInt(value, 10) });
            if (this.global.Messaging.currentUser) {
                this._saveSettings();
            }
        },
        /**
         * @param {event} ev
         */
        async setPushToTalkKey(ev) {
            const pushToTalkKey = `${ev.shiftKey || ''}.${ev.ctrlKey || ev.metaKey || ''}.${ev.altKey || ''}.${ev.key}`;
            this.update({ localPushToTalkKey: pushToTalkKey });
            if (this.global.Messaging.currentUser) {
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
                this.global.Messaging.browser.clearTimeout(this.volumeSettingsTimeouts[partnerId]);
            }
            this.update({
                volumeSettingsTimeouts: {
                    ...this.volumeSettingsTimeouts,
                    [partnerId]: this.global.Messaging.browser.setTimeout(
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
            await this.global.Rtc.updateVoiceActivation();
        },
        async togglePushToTalk() {
            this.update({ localUsePushToTalk: !this.usePushToTalk });
            await this.global.Rtc.updateVoiceActivation();
            if (this.global.Messaging.currentUser) {
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
        _onChangeUseBlur() {
            if (!this.global.Rtc.sendUserVideo) {
                return;
            }
            this.global.Rtc.toggleUserVideo({ force: true });
        },
        /**
         * @private
         * @param {Event} ev
         */
        async _onStorage(ev) {
            if (ev.key === 'mail_user_setting_voice_threshold') {
                this.update({ voiceActivationThreshold: ev.newValue });
                await this.global.Rtc.updateVoiceActivation();
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
            await this.global.Messaging.rpc(
                {
                    model: 'res.users.settings',
                    method: 'set_res_users_settings',
                    args: [[this.global.Messaging.currentUser.res_users_settings_id.id], {
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
            await this.global.Messaging.rpc(
                {
                    model: 'res.users.settings',
                    method: 'set_volume_setting',
                    args: [
                        [this.global.Messaging.currentUser.res_users_settings_id.id],
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
            this.global.Messaging.browser.clearTimeout(this.globalSettingsTimeout);
            this.update({
                globalSettingsTimeout: this.global.Messaging.browser.setTimeout(
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
        backgroundBlurAmount: attr({
            default: 10,
        }),
        edgeBlurAmount: attr({
            default: 10,
        }),
        globalSettingsTimeout: attr(),
        /**
         * true if listening to keyboard input to register the push to talk key.
         */
        isRegisteringKey: attr({
            default: false,
        }),
        localPushToTalkKey: attr(),
        localUsePushToTalk: attr(),
        localVoiceActiveDuration: attr(),
        /**
         * String that encodes the push-to-talk key with its modifiers.
         */
        pushToTalkKey: attr({
            compute() {
                if (this.localPushToTalkKey !== undefined) {
                    return this.localPushToTalkKey;
                }
                if (!this.global.Messaging.currentUser) {
                    return clear();
                }
                if (!this.global.Messaging.currentUser.res_users_settings_id) {
                    return clear();
                }
                return this.global.Messaging.currentUser.res_users_settings_id.push_to_talk_key;
            },
            default: '',
        }),
        useBlur: attr({
            default: false,
        }),
        /**
         * If true, push-to-talk will be used over voice activation.
         */
        usePushToTalk: attr({
            compute() {
                if (this.localUsePushToTalk !== undefined) {
                    return this.localUsePushToTalk;
                }
                if (!this.global.Messaging.currentUser) {
                    return clear();
                }
                if (!this.global.Messaging.currentUser.res_users_settings_id) {
                    return clear();
                }
                return this.global.Messaging.currentUser.res_users_settings_id.use_push_to_talk;
            },
            default: false,
        }),
        /**
         * Normalized volume at which the voice activation system must consider the user as "talking".
         */
        voiceActivationThreshold: attr({
            default: 0.05,
        }),
        /**
         * Duration in milliseconds the voice remains active after releasing the
         * push-to-talk key.
         */
        voiceActiveDuration: attr({
            compute() {
                if (this.localVoiceActiveDuration !== undefined) {
                    return this.localVoiceActiveDuration;
                }
                if (!this.global.Messaging.currentUser) {
                    return clear();
                }
                if (!this.global.Messaging.currentUser.res_users_settings_id) {
                    return clear();
                }
                return this.global.Messaging.currentUser.res_users_settings_id.voice_active_duration;
            },
            default: 0,
        }),
        volumeSettingsTimeouts: attr({
            default: {},
        }),
    },
    onChanges: [
        {
            dependencies: ['useBlur'],
            methodName: '_onChangeUseBlur',
        },
    ],
});
