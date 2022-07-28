/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { clear } from '@mail/model/model_field_command';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'CallSettingsMenu',
    identifyingMode: 'xor',
    lifecycleHooks: {
        _created() {
            browser.addEventListener('keydown', this._onKeyDown);
            browser.addEventListener('keyup', this._onKeyUp);
        },
        _willDelete() {
            browser.removeEventListener('keydown', this._onKeyDown);
            browser.removeEventListener('keyup', this._onKeyUp);
        },
    },
    recordMethods: {
        /**
         * @param {Event} ev
         */
        onChangeDelay(ev) {
            this.userSetting.setDelayValue(ev.target.value);
        },
        onChangePushToTalk() {
            if (this.userSetting.usePushToTalk) {
                this.userSetting.update({
                    isRegisteringKey: false,
                });
            }
            this.userSetting.togglePushToTalk();
        },
        /**
         * @param {Event} ev
         */
        onChangeSelectAudioInput(ev) {
            this.userSetting.setAudioInputDevice(ev.target.value);
        },
        /**
         * @param {MouseEvent} ev
         */
        onChangeThreshold(ev) {
            this.userSetting.setThresholdValue(parseFloat(ev.target.value));
        },
        /**
         * @param {Event} ev
         */
        onChangeVideoFilterCheckbox(ev) {
            const showOnlyVideo = ev.target.checked;
            this.thread.channel.update({ showOnlyVideo });
            if (!this.callView) {
                return;
            }
            const activeRtcSession = this.callView.activeRtcSession;
            if (showOnlyVideo && activeRtcSession && !activeRtcSession.videoStream) {
                this.callView.update({ activeRtcSession: clear() });
            }
        },
        onClickRegisterKeyButton() {
            this.userSetting.update({
                isRegisteringKey: !this.isRegisteringKey,
            });
        },
        _computeCallView() {
            if (this.threadViewOwner) {
                return this.threadViewOwner.callView;
            }
            if (this.chatWindowOwner && this.chatWindowOwner.threadView) {
                return this.chatWindowOwner.threadView.callView;
            }
            return clear();
        },
        _computeThread() {
            if (this.threadViewOwner) {
                return this.threadViewOwner.thread;
            }
            if (this.chatWindowOwner) {
                return this.chatWindowOwner.thread;
            }
            return clear();
        },
        _onKeyDown(ev) {
            if (!this.userSetting.isRegisteringKey) {
                return;
            }
            ev.stopPropagation();
            ev.preventDefault();
            this.userSetting.setPushToTalkKey(ev);
        },
        _onKeyUp(ev) {
            if (!this.userSetting.isRegisteringKey) {
                return;
            }
            ev.stopPropagation();
            ev.preventDefault();
            this.userSetting.update({
                isRegisteringKey: false,
            });
        },
    },
    fields: {
        callView: one('CallView', {
            compute: '_computeCallView',
        }),
        chatWindowOwner: one('ChatWindow', {
            identifying: true,
            inverse: 'callSettingsMenu',
        }),
        thread: one('Thread', {
            compute: '_computeThread',
        }),
        threadViewOwner: one('ThreadView', {
            identifying: true,
            inverse: 'callSettingsMenu',
        }),
        userSetting: one('UserSetting', {
            related: 'messaging.userSetting',
        }),
    },
});
