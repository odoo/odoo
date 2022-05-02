/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

registerModel({
    name: 'SoundEffects',
    identifyingFields: ['Record/messaging'],
    fields: {
        channelJoin: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.3, 'SoundEffect/filename': 'channel_01_in' }),
            isCausal: true,
        }),
        channelLeave: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/filename': 'channel_04_out' }),
            isCausal: true,
        }),
        deafen: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.15, 'SoundEffect/filename': 'deafen_new_01' }),
            isCausal: true,
        }),
        incomingCall: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.15, 'SoundEffect/filename': 'call_02_in_' }),
            isCausal: true,
        }),
        memberLeave: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.5, 'SoundEffect/filename': 'channel_01_out' }),
            isCausal: true,
        }),
        mute: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.2, 'SoundEffect/filename': 'mute_1' }),
            isCausal: true,
        }),
        newMessage: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/filename': 'dm_02' }),
            isCausal: true,
        }),
        pushToTalkOn: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.05, 'SoundEffect/filename': 'ptt_push_1' }),
            isCausal: true,
        }),
        pushToTalkOff: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.05, 'SoundEffect/filename': 'ptt_release_1' }),
            isCausal: true,
        }),
        screenSharing: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.5, 'SoundEffect/filename': 'share_02' }),
            isCausal: true,
        }),
        undeafen: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.15, 'SoundEffect/filename': 'undeafen_new_01' }),
            isCausal: true,
        }),
        unmute: one('SoundEffect', {
            default: insertAndReplace({ 'SoundEffect/defaultVolume': 0.2, 'SoundEffect/filename': 'unmute_1' }),
            isCausal: true,
        }),
    },
});
