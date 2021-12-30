/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'SoundEffects',
    identifyingFields: ['messaging'],
    fields: {
        channelJoin: one('SoundEffect', {
            default: insertAndReplace({ filename: 'channel_01_in' }),
            isCausal: true,
        }),
        channelLeave: one('SoundEffect', {
            default: insertAndReplace({ filename: 'channel_04_out' }),
            isCausal: true,
        }),
        deafen: one('SoundEffect', {
            default: insertAndReplace({ filename: 'deafen_new_01' }),
            isCausal: true,
        }),
        incomingCall: one('SoundEffect', {
            default: insertAndReplace({ filename: 'call_02_in_' }),
            isCausal: true,
        }),
        memberLeave: one('SoundEffect', {
            default: insertAndReplace({ filename: 'channel_01_out' }),
            isCausal: true,
        }),
        mute: one('SoundEffect', {
            default: insertAndReplace({ filename: 'mute_1' }),
            isCausal: true,
        }),
        newMessage: one('SoundEffect', {
            default: insertAndReplace({ filename: 'dm_02' }),
            isCausal: true,
        }),
        pushToTalkOn: one('SoundEffect', {
            default: insertAndReplace({ filename: 'ptt_push_1' }),
            isCausal: true,
        }),
        pushToTalkOff: one('SoundEffect', {
            default: insertAndReplace({ filename: 'ptt_release_1' }),
            isCausal: true,
        }),
        screenSharing: one('SoundEffect', {
            default: insertAndReplace({ filename: 'share_02' }),
            isCausal: true,
        }),
        undeafen: one('SoundEffect', {
            default: insertAndReplace({ filename: 'undeafen_new_01' }),
            isCausal: true,
        }),
        unmute: one('SoundEffect', {
            default: insertAndReplace({ filename: 'unmute_1' }),
            isCausal: true,
        }),
    },
});
