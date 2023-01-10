/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class RtcConfigurationMenu extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            const res = super._created(...arguments);
            this._onKeyDown = this._onKeyDown.bind(this);
            this._onKeyUp = this._onKeyUp.bind(this);
            browser.addEventListener('keydown', this._onKeyDown);
            browser.addEventListener('keyup', this._onKeyUp);
            return res;
        }

        /**
         * @override
         */
        _willDelete() {
            browser.removeEventListener('keydown', this._onKeyDown);
            browser.removeEventListener('keyup', this._onKeyUp);
            return super._willDelete(...arguments);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {String} value
         */
        onChangeDelay(value) {
            this.userSetting.setDelayValue(value);
        }

        onChangePushToTalk() {
            if (this.userSetting.usePushToTalk) {
                this.update({
                    isRegisteringKey: false,
                });
            }
            this.userSetting.togglePushToTalk();
        }

        /**
         * @param {String} value
         */
        onChangeSelectAudioInput(value) {
            this.userSetting.setAudioInputDevice(value);
        }

        /**
         * @param {String} value
         */
        onChangeThreshold(value) {
            this.userSetting.setThresholdValue(parseFloat(value));
        }

        onClickRegisterKeyButton() {
            this.update({
                isRegisteringKey: !this.isRegisteringKey,
            });
        }

        toggle() {
            this.update({ isOpen: !this.isOpen });
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        _onKeyDown(ev) {
            if (!this.isRegisteringKey) {
                return;
            }
            ev.stopPropagation();
            ev.preventDefault();
            this.userSetting.setPushToTalkKey(ev);
        }

        _onKeyUp(ev) {
            if (!this.isRegisteringKey) {
                return;
            }
            ev.stopPropagation();
            ev.preventDefault();
            this.update({
                isRegisteringKey: false,
            });
        }

    }

    RtcConfigurationMenu.fields = {
        isOpen: attr({
            default: false,
        }),
        /**
         * true if listening to keyboard input to register the push to talk key.
         */
        isRegisteringKey: attr({
            default: false,
        }),
        userSetting: one2one('mail.user_setting', {
            inverse: 'rtcConfigurationMenu',
            readonly: true,
            required: true,
        }),
    };
    RtcConfigurationMenu.identifyingFields = ['userSetting'];
    RtcConfigurationMenu.modelName = 'mail.rtc_configuration_menu';

    return RtcConfigurationMenu;
}

registerNewModel('mail.rtc_configuration_menu', factory);
