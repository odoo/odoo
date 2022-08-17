/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'CallSettingsMenu',
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
                this.update({
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
        userSetting: one('UserSetting', {
            identifying: true,
            inverse: 'callSettingsMenu',
        }),
    },
});
