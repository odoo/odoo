/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
import { create } from '@mail/model/model_field_command';

function factory(dependencies) {

    class SoundEffects extends dependencies['mail.model'] {

        /**
         * @override
         */
        static _createRecordLocalId(data) {
            return _.uniqueId(`${this.modelName}_`);
        }
    }

    SoundEffects.fields = {
        channelJoin: one2one('mail.sound_effect', {
            default: create({ filename: 'channel_01_in' }),
            isCausal: true,
        }),
        channelLeave: one2one('mail.sound_effect', {
            /**
             * FIXME This file is faulty on at least chrome.
             * task-id for the sound effects: 2554674
             */
            default: create({ filename: 'channel_04_out' }),
            isCausal: true,
        }),
        incomingCall: one2one('mail.sound_effect', {
            default: create({ filename: 'call_02_in_' }),
            isCausal: true,
        }),
        memberLeave: one2one('mail.sound_effect', {
            default: create({ filename: 'channel_01_out' }),
            isCausal: true,
        }),
        newMessage: one2one('mail.sound_effect', {
            default: create({ filename: 'dm_02' }),
            isCausal: true,
        }),
        pushToTalk: one2one('mail.sound_effect', {
            default: create({ filename: 'dm_01' }),
            isCausal: true,
        }),
        screenSharing: one2one('mail.sound_effect', {
            default: create({ filename: 'share_02' }),
            isCausal: true,
        }),
    };

    SoundEffects.modelName = 'mail.sound_effects';

    return SoundEffects;
}

registerNewModel('mail.sound_effects', factory);
