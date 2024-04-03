/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'SoundEffects',
    fields: {
        channelJoin: one('SoundEffect', {
            default: { defaultVolume: 0.3, filename: 'channel_01_in' },
            isCausal: true,
        }),
        channelLeave: one('SoundEffect', {
            default: { filename: 'channel_04_out' },
            isCausal: true,
        }),
        deafen: one('SoundEffect', {
            default: { defaultVolume: 0.15, filename: 'deafen_new_01' },
            isCausal: true,
        }),
        incomingCall: one('SoundEffect', {
            default: { defaultVolume: 0.15, filename: 'call_02_in_' },
            isCausal: true,
        }),
        memberLeave: one('SoundEffect', {
            default: { defaultVolume: 0.5, filename: 'channel_01_out' },
            isCausal: true,
        }),
        mute: one('SoundEffect', {
            default: { defaultVolume: 0.2, filename: 'mute_1' },
            isCausal: true,
        }),
        newMessage: one('SoundEffect', {
            default: { filename: 'dm_02' },
            isCausal: true,
        }),
        pushToTalkOn: one('SoundEffect', {
            default: { defaultVolume: 0.05, filename: 'ptt_push_1' },
            isCausal: true,
        }),
        pushToTalkOff: one('SoundEffect', {
            default: { defaultVolume: 0.05, filename: 'ptt_release_1' },
            isCausal: true,
        }),
        screenSharing: one('SoundEffect', {
            default: { defaultVolume: 0.5, filename: 'share_02' },
            isCausal: true,
        }),
        undeafen: one('SoundEffect', {
            default: { defaultVolume: 0.15, filename: 'undeafen_new_01' },
            isCausal: true,
        }),
        unmute: one('SoundEffect', {
            default: { defaultVolume: 0.2, filename: 'unmute_1' },
            isCausal: true,
        }),
    },
});
