/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'mail.sound_effects',
    identifyingFields: ['messaging'],
    fields: {
        channelJoin: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'channel_01_in' }),
            isCausal: true,
        }),
        channelLeave: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'channel_04_out' }),
            isCausal: true,
        }),
        incomingCall: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'call_02_in_' }),
            isCausal: true,
        }),
        memberLeave: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'channel_01_out' }),
            isCausal: true,
        }),
        newMessage: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'dm_02' }),
            isCausal: true,
        }),
        pushToTalk: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'dm_01' }),
            isCausal: true,
        }),
        screenSharing: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'share_02' }),
            isCausal: true,
        }),
    },
});
