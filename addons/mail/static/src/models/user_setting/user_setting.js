/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one, one2many } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class UserSetting extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            const res = super._created(...arguments);
            this._timeoutIds = {};
            this._loadLocalSettings();
            this._onStorage = this._onStorage.bind(this);
            browser.addEventListener('storage', this._onStorage);
            return res;
        }

        /**
         * @override
         */
        _willDelete() {
            browser.removeEventListener('storage', this._onStorage);
            for (const timeoutId of Object.values(this._timeoutIds)) {
                browser.clearTimeout(timeoutId);
            }
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @static
         * @param {Object} data
         * @returns {Object}
         */
        static convertData(data) {
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
        }

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
        }

        /**
         * @param {event} ev
         */
        isPushToTalkKey(ev) {
            if (!this.usePushToTalk || !this.pushToTalkKey) {
                return;
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

        pushToTalkKeyToString() {
            const { shiftKey, ctrlKey, altKey, key } = this.pushToTalkKeyFormat();
            const f = (k, name) => k ? name : '';
            const keys = [
                f(ctrlKey, 'Ctrl'), f(altKey, 'Alt'), f(shiftKey, 'Shift'), key === " " ? "Space": key
            ].filter(Boolean);
            return keys.join(" + ");
        }

        /**
         * @param {String} audioInputDeviceId
         */
        async setAudioInputDevice(audioInputDeviceId) {
            this.update({
                audioInputDeviceId,
            });
            this.env.services.local_storage.setItem('mail_user_setting_audio_input_device_id', audioInputDeviceId);
            await this.messaging.rtc.updateLocalAudioTrack(true);
        }

        /**
         * @param {String} value
         */
        setDelayValue(value) {
            const voiceActiveDuration = parseInt(value, 10);
            this.update({ voiceActiveDuration });
            if (!this.messaging.isCurrentUserGuest) {
                this._saveSettings();
            }
        }

        /**
         * @param {event} ev
         */
        async setPushToTalkKey(ev) {
            const nonElligibleKeys = new Set(['Shift', 'Control', 'Alt', 'Meta']);
            let pushToTalkKey = `${ev.shiftKey || ''}.${ev.ctrlKey || ev.metaKey || ''}.${ev.altKey || ''}`;
            if (!nonElligibleKeys.has(ev.key)) {
                pushToTalkKey += `.${ev.key}`;
            }
            this.update({ pushToTalkKey });
            if (!this.messaging.isCurrentUserGuest) {
                this._saveSettings();
            }
        }

        /**
         * @param {Object} param0
         * @param {number} [param0.guestId]
         * @param {number} [param0.partnerId]
         * @param {number} param0.volume
         */
        async saveVolumeSetting({ guestId, partnerId, volume }) {
            this._debounce(async () => {
                await this.async(() => this.env.services.rpc(
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
                ));
            }, 5000, `sound_${partnerId}`);
        }

        /**
         * @param {float} voiceActivationThreshold
         */
        async setThresholdValue(voiceActivationThreshold) {
            this.update({ voiceActivationThreshold });
            this.env.services.local_storage.setItem('mail_user_setting_voice_threshold', voiceActivationThreshold);
            await this.messaging.rtc.updateVoiceActivation();
        }

        async togglePushToTalk() {
            this.update({ usePushToTalk: !this.usePushToTalk });
            await this.messaging.rtc.updateVoiceActivation();
            if (!this.messaging.isCurrentUserGuest) {
                this._saveSettings();
            }
        }

        toggleLayoutSettingsWindow() {
            this.update({ isRtcLayoutSettingDialogOpen: !this.isRtcLayoutSettingDialogOpen });
        }

        /**
         * toggles the display of the option window
         */
        toggleWindow() {
            this.update({ isOpen: !this.isOpen });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         * @param {function} f
         * @param {number} delay in ms
         * @param {any} key
         */
        _debounce(f, delay, key) {
            this._timeoutIds[key] && browser.clearTimeout(this._timeoutIds[key]);
            this._timeoutIds[key] = browser.setTimeout(() => {
                if (!this.exists()) {
                    return;
                }
                f();
            }, delay);
        }

        /**
         * @private
         */
        _loadLocalSettings() {
            const voiceActivationThresholdString = this.env.services.local_storage.getItem(
                "mail_user_setting_voice_threshold"
            );
            const audioInputDeviceId = this.env.services.local_storage.getItem(
                "mail_user_setting_audio_input_device_id"
            );
            this.update({
                voiceActivationThreshold: voiceActivationThresholdString ? parseFloat(voiceActivationThresholdString) : undefined,
                audioInputDeviceId: audioInputDeviceId || undefined,
            });
        }

        /**
         * @private
         */
        async _saveSettings() {
            this._debounce(async () => {
                await this.async(() => this.env.services.rpc(
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
                ));
            }, 2000, 'globalSettings');
        }

        /**
         * @private
         * @param {Event} ev
         */
        async _onStorage(ev) {
            if (ev.key === 'mail_user_setting_voice_threshold') {
                this.update({ voiceActivationThreshold: ev.newValue });
                await this.messaging.rtc.updateVoiceActivation();
            }
        }

    }

    UserSetting.fields = {
        /**
         * DeviceId of the audio input selected by the user
         */
        audioInputDeviceId: attr({
            default: '',
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        /**
         * true if the dialog for the call viewer layout is open
         */
        isRtcLayoutSettingDialogOpen: attr({
            default: false,
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
        rtcConfigurationMenu: one2one('mail.rtc_configuration_menu', {
            default: insertAndReplace(),
            inverse: 'userSetting',
            isCausal: true,
            required: true,
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
         * Models that represent the volume chosen by the user for each partner.
         */
        volumeSettings: one2many('mail.volume_setting', {
            inverse: 'userSetting',
            isCausal: true,
        }),
    };
    UserSetting.identifyingFields = ['id'];
    UserSetting.modelName = 'mail.user_setting';

    return UserSetting;
}

registerNewModel('mail.user_setting', factory);
