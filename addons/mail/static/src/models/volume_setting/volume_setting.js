/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one, many2one } from '@mail/model/model_field';
import { insert } from '@mail/model/model_field_command';
import { OnChange } from '@mail/model/model_onchange';

function factory(dependencies) {

    class VolumeSetting extends dependencies['mail.model'] {


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
            if ('volume' in data) {
                data2.volume = data.volume;
            }
            if ('id' in data) {
                data2.id = data.id;
            }

            // relations
            if ('partner_id' in data) {
                const partnerNameGet = data['partner_id'];
                const partnerData = {
                    display_name: partnerNameGet[1],
                    id: partnerNameGet[0],
                };
                data2.partner = insert(partnerData);
            }
            return data2;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @private
         */
        _onChangeVolume() {
            for (const rtcSession of this.partner.rtcSessions) {
                if (rtcSession.audioElement) {
                    rtcSession.audioElement.volume = this.volume;
                }
            }
        }
    }

    VolumeSetting.fields = {
        id: attr({
            readonly: true,
            required: true,
        }),
        partner: one2one('mail.partner', {
            inverse: 'volumeSetting',
            required: true,
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
