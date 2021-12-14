/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'SoundEffects',
    identifyingFields: ['messaging'],
    fields: {
        channelJoin: one2one('SoundEffect', {
            default: insertAndReplace({ filename: 'channel_01_in' }),
            isCausal: true,
        }),
        channelLeave: one2one('SoundEffect', {
            default: insertAndReplace({ filename: 'channel_04_out' }),
            isCausal: true,
        }),
        incomingCall: one2one('SoundEffect', {
            default: insertAndReplace({ filename: 'call_02_in_' }),
            isCausal: true,
        }),
        memberLeave: one2one('SoundEffect', {
            default: insertAndReplace({ filename: 'channel_01_out' }),
            isCausal: true,
        }),
        newMessage: one2one('SoundEffect', {
            default: insertAndReplace({ filename: 'dm_02' }),
            isCausal: true,
        }),
        pushToTalk: one2one('SoundEffect', {
            default: insertAndReplace({ filename: 'dm_01' }),
            isCausal: true,
        }),
        screenSharing: one2one('SoundEffect', {
            default: insertAndReplace({ filename: 'share_02' }),
            isCausal: true,
        }),
    },
});
