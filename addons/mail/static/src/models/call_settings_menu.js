/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'CallSettingsMenu',
    identifyingFields: ['userSetting'],
    lifecycleHooks: {
        _created() {
            browser.addEventListener('keydown', this._onKeyDown);
            browser.addEventListener('keyup', this._onKeyUp);
            this._loadMediaDevices();
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
        /**
         * @private
         */
        async _loadMediaDevices() {
            try {
                const mediaDevicesData = await browser.navigator.mediaDevices.enumerateDevices();
                this.messaging.update({
                    mediaDevices: insertAndReplace(
                        mediaDevicesData.map(
                            data => {
                                return {
                                    id: data.deviceId,
                                    kind: data.kind,
                                    label: data.label,
                                };
                            },
                        ),
                    ),
                });
            } catch (_err) {
                this.messaging.update({ mediaDevices: clear() });
            }
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
        inputSelection: one('InputSelection', {
            default: insertAndReplace(),
            isCausal: true,
            inverse: 'callSettingsMenuOwner',
        }),
        userSetting: one('UserSetting', {
            inverse: 'callSettingsMenu',
            readonly: true,
        }),
    },
});
