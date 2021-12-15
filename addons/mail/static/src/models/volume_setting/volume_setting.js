/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one, many2one } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'VolumeSetting',
    identifyingFields: ['id'],
    recordMethods: {
        /**
         * @private
         */
        _onChangeVolume() {
            let rtcSessions;
            if (this.partner) {
                rtcSessions = this.partner.rtcSessions;
            } else if (this.guest) {
                rtcSessions = this.guest.rtcSessions;
            } else {
                return;
            }
            for (const rtcSession of rtcSessions) {
                if (rtcSession.audioElement) {
                    rtcSession.audioElement.volume = this.volume;
                }
            }
        },
    },
    fields: {
        guest: one2one('Guest', {
            inverse: 'volumeSetting',
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        partner: one2one('Partner', {
            inverse: 'volumeSetting',
        }),
        userSetting: many2one('UserSetting', {
            inverse: 'volumeSettings',
            required: true,
        }),
        volume: attr({
            default: 0.5,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['volume'],
            methodName: '_onChangeVolume',
        }),
    ],
});
