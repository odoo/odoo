/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

registerModel({
    name: 'RtcConfigurationMenu',
    identifyingFields: ['userSetting'],
    lifecycleHooks: {
        _created() {
            this._onKeyDown = this._onKeyDown.bind(this);
            this._onKeyUp = this._onKeyUp.bind(this);
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
         * @param {String} value
         */
        onChangeDelay(value) {
            this.userSetting.setDelayValue(value);
        },
        onChangePushToTalk() {
            if (this.userSetting.usePushToTalk) {
                this.update({
                    isRegisteringKey: false,
                });
            }
            this.userSetting.togglePushToTalk();
        },
        /**
         * @param {String} value
         */
        onChangeSelectAudioInput(value) {
            this.userSetting.setAudioInputDevice(value);
        },
        /**
         * @param {String} value
         */
        onChangeThreshold(value) {
            this.userSetting.setThresholdValue(parseFloat(value));
        },
        onClickRegisterKeyButton() {
            this.update({
                isRegisteringKey: !this.isRegisteringKey,
            });
        },
        toggle() {
            this.update({ isOpen: !this.isOpen });
        },
        _onKeyDown(ev) {
            if (!this.isRegisteringKey) {
                return;
            }
            ev.stopPropagation();
            ev.preventDefault();
            this.userSetting.setPushToTalkKey(ev);
        },
        _onKeyUp(ev) {
            if (!this.isRegisteringKey) {
                return;
            }
            ev.stopPropagation();
            ev.preventDefault();
            this.update({
                isRegisteringKey: false,
            });
        },
    },
    fields: {
        isOpen: attr({
            default: false,
        }),
        /**
         * true if listening to keyboard input to register the push to talk key.
         */
        isRegisteringKey: attr({
            default: false,
        }),
        userSetting: one2one('UserSetting', {
            inverse: 'rtcConfigurationMenu',
            readonly: true,
            required: true,
        }),
    },
});
