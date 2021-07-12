/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one, one2many } from '@mail/model/model_field';
import { create } from '@mail/model/model_field_command';

function factory(dependencies) {

    class UserSetting extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            const res = super._created(...arguments);
            this._timeoutIds = {};
            this._loadLocalSettings();
            this._onFullScreenChange = this._onFullScreenChange.bind(this);
            browser.addEventListener('fullscreenchange', this._onFullScreenChange);
            return res;
        }

        /**
         * @override
         */
        _willDelete() {
            for (const timeoutId of Object.values(this._timeoutIds)) {
                browser.clearTimeout(timeoutId);
            }
            browser.removeEventListener('fullscreenchange', this._onFullScreenChange);
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
        }

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
        }

        pushToTalkKeyToString() {
            const { shiftKey, ctrlKey, altKey, key } = this.pushToTalkKeyFormat();
            const f = (k, name) => k ? name : '';
            return `${f(ctrlKey, 'Ctrl + ')}${f(altKey, 'Alt + ')}${f(shiftKey, 'Shift + ')}${key}`;
        }

        /**
         * @param {String} audioInputDeviceId
         */
        async setAudioInputDevice(audioInputDeviceId) {
            this.update({
                audioInputDeviceId,
            });
            this.env.services.local_storage.setItem('mail_user_setting_audio_input_device_id', audioInputDeviceId);
            await this.messaging.mailRtc.updateLocalAudioTrack(true);
        }

        /**
         * @param {String} value
         */
        setDelayValue(value) {
            const voiceActiveDuration = parseInt(value, 10);
            this.update({ voiceActiveDuration });
            this._saveSettings();
        }

        /**
         * @param {event} ev
         */
        async setPushToTalkKey(ev) {
            const pushToTalkKey = `${ev.shiftKey || ''}.${ev.ctrlKey || ev.metaKey || ''}.${ev.altKey || ''}.${ev.key}`;
            this.update({ pushToTalkKey });
            this._saveSettings();
        }

        /**
         * @param {String} rtcLayout
         */
        setRtcLayout(rtcLayout) {
            this.update({ rtcLayout });
        }

        /**
         * @param {mail.partner} partner
         * @param {number} volume
         */
        async saveVolumeSetting(partnerId, volume) {
            this._debounce(async () => {
                await this.async(() => this.env.services.rpc(
                    {
                        model: 'mail.user.settings',
                        method: 'set_volume_setting',
                        args: [
                            [this.messaging.mailUserSettingsId],
                            partnerId,
                            volume,
                        ],
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
            await this.messaging.mailRtc.updateVoiceActivation();
        }

        /**
         * @param {boolean} force Force the fullScreen state.
         */
        async toggleFullScreen(force) {
            const el = document.body;
            const fullScreenElement = document.webkitFullscreenElement || document.fullscreenElement;
            if (force !== undefined ? force : !fullScreenElement) {
                try {
                    if (el.requestFullscreen) {
                        await el.requestFullscreen();
                    } else if (el.mozRequestFullScreen) {
                        await el.mozRequestFullScreen();
                    } else if (el.webkitRequestFullscreen) {
                        await el.webkitRequestFullscreen();
                    }
                    this.update({ isRtcCallViewerFullScreen: true });
                } catch (e) {
                    this.update({ isRtcCallViewerFullScreen: false });
                }
                return;
            }
            if (fullScreenElement) {
                if (document.exitFullscreen) {
                    await document.exitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    await document.mozCancelFullScreen();
                } else if (document.webkitCancelFullScreen) {
                    await document.webkitCancelFullScreen();
                }
                this.update({ isRtcCallViewerFullScreen: false });
            }
        }

        async togglePushToTalk() {
            this.update({ usePushToTalk: !this.usePushToTalk });
            await this.messaging.mailRtc.updateVoiceActivation();
            this._saveSettings();
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
            const voiceActivationThreshold = parseFloat(voiceActivationThresholdString);
            if (voiceActivationThreshold > 0) {
                this.update({
                    voiceActivationThreshold,
                    audioInputDeviceId,
                });
            }
        }

        /**
         * @private
         */
        async _saveSettings() {
            this._debounce(async () => {
                await this.async(() => this.env.services.rpc(
                    {
                        model: 'mail.user.settings',
                        method: 'set_mail_user_settings',
                        args: [[this.messaging.mailUserSettingsId], {
                            push_to_talk_key: this.pushToTalkKey,
                            use_push_to_talk: this.usePushToTalk,
                            voice_active_duration: this.voiceActiveDuration,
                        }],
                    },
                    { shadow: true },
                ));
            }, 2000, 'globalSettings');
        }

        //----------------------------------------------------------------------
        // Handlers
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _onFullScreenChange() {
            const fullScreenElement = document.webkitFullscreenElement || document.fullscreenElement;
            if (fullScreenElement) {
                this.update({ isRtcCallViewerFullScreen: true });
                return;
            }
            this.update({ isRtcCallViewerFullScreen: false });
        }
    }

    UserSetting.fields = {
        /**
         * DeviceId of the audio input selected by the user
         */
        audioInputDeviceId: attr({
            default: '',
        }),
        id: attr(),
        /**
         * true if the rtcCallViewer has to be fullScreen
         */
        isRtcCallViewerFullScreen: attr({
            default: false,
        }),
        /**
         * true if the dialog for the call viewer layout is open
         */
        isRtcLayoutSettingDialogOpen: attr({
            default: false,
        }),
        messaging: one2one('mail.messaging', {
            inverse: 'userSetting',
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
            default: create(),
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
         * true if we want to filter out non-videos from the rtc session display
         */
        rtcFilterVideoGrid: attr({
            default: false,
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
            default: 0.2,
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

    UserSetting.modelName = 'mail.user_setting';

    return UserSetting;
}

registerNewModel('mail.user_setting', factory);
