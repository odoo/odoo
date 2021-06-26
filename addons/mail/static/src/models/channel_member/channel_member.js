/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';
import { insert, unlink } from '@mail/model/model_field_command';

function factory(dependencies) {

    class ChannelMember extends dependencies['mail.model'] {

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
            if ('id' in data) {
                data2.id = data.id;
            }
            // relations
            if ('partner' in data) {
                if (!data.partner) {
                    data2.partner = unlink();
                } else {
                    const convertedPartnerData = this.env.models['mail.partner'].convertData(data.partner);
                    data2.partner = insert(convertedPartnerData);
                }
            }
            return data2;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }
    }

    ChannelMember.fields = {
        id: attr({
            required: true,
        }),
        /**
         * The the partner who is the member of the channel.
         */
        partner: many2one('mail.partner', {
            required: true,
        }),
        /**
         * The thread for which it is the the member of.
         */
        thread: many2one('mail.thread', {
            inverse: 'members',
            required: true,
        }),
    };

    ChannelMember.modelName = 'mail.channel_member';

    return ChannelMember;
}

registerNewModel('mail.channel_member', factory);
