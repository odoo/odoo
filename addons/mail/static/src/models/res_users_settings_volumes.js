/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

/**
 * Mirrors the fields of the python model res.users.settings.volumes.
 */
registerModel({
    name: 'res.users.settings.volumes',
    recordMethods: {
        /**
         * @private
         */
        _onChangeVolume() {
            const { rtcSessions } = this.partner_id || this.guest_id;
            if (!rtcSessions) {
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
        guest_id: one('Guest', {
            inverse: 'volumeSetting',
        }),
        id: attr({
            identifying: true,
        }),
        partner_id: one('Partner', {
            inverse: 'volumeSetting',
        }),
        user_setting_id: one('res.users.settings', {
            inverse: 'volume_settings_ids',
            readonly: true,
            required: true,
        }),
        volume: attr({
            default: 0.5,
        }),
    },
    onChanges: [
        {
            dependencies: ['volume'],
            methodName: '_onChangeVolume',
        },
    ],
});
