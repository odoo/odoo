/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'AudioRegistry',
    fields: {
        channelJoin: one('Audio', {
            default: { defaultVolume: 0.3, filename: 'channel_01_in' },
            isCausal: true,
        }),
        channelLeave: one('Audio', {
            default: { filename: 'channel_04_out' },
            isCausal: true,
        }),
        deafen: one('Audio', {
            default: { defaultVolume: 0.15, filename: 'deafen_new_01' },
            isCausal: true,
        }),
        incomingCall: one('Audio', {
            default: { defaultVolume: 0.15, filename: 'call_02_in_' },
            isCausal: true,
        }),
        memberLeave: one('Audio', {
            default: { defaultVolume: 0.5, filename: 'channel_01_out' },
            isCausal: true,
        }),
        mute: one('Audio', {
            default: { defaultVolume: 0.2, filename: 'mute_1' },
            isCausal: true,
        }),
        newMessage: one('Audio', {
            default: { filename: 'dm_02' },
            isCausal: true,
        }),
        pushToTalkOn: one('Audio', {
            default: { defaultVolume: 0.05, filename: 'ptt_push_1' },
            isCausal: true,
        }),
        pushToTalkOff: one('Audio', {
            default: { defaultVolume: 0.05, filename: 'ptt_release_1' },
            isCausal: true,
        }),
        screenSharing: one('Audio', {
            default: { defaultVolume: 0.5, filename: 'share_02' },
            isCausal: true,
        }),
        undeafen: one('Audio', {
            default: { defaultVolume: 0.15, filename: 'undeafen_new_01' },
            isCausal: true,
        }),
        unmute: one('Audio', {
            default: { defaultVolume: 0.2, filename: 'unmute_1' },
            isCausal: true,
        }),
    },
});
