/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one, many2one } from '@mail/model/model_field';
import { insert } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

function factory(dependencies) {

    class VolumeSetting extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

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
        }
    }

    VolumeSetting.fields = {
        guest: one2one('mail.guest', {
            inverse: 'volumeSetting',
        }),
        id: attr({
            readonly: true,
            required: true,
        }),
        partner: one2one('mail.partner', {
            inverse: 'volumeSetting',
        }),
        userSetting: many2one('mail.user_setting', {
            inverse: 'volumeSettings',
            required: true,
        }),
        volume: attr({
            default: 0.5,
        }),
    };
    VolumeSetting.identifyingFields = ['id'];
    VolumeSetting.onChanges = [
        new OnChange({
            dependencies: ['volume'],
            methodName: '_onChangeVolume',
        }),
    ];

    VolumeSetting.modelName = 'mail.volume_setting';

    return VolumeSetting;
}

registerNewModel('mail.volume_setting', factory);
