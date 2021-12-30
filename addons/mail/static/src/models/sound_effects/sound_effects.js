/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { one2one } from '@mail/model/model_field';
import { insertAndReplace } from '@mail/model/model_field_command';

function factory(dependencies) {

    class SoundEffects extends dependencies['mail.model'] {
    }

    SoundEffects.fields = {
        channelJoin: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'channel_01_in' }),
            isCausal: true,
        }),
        channelLeave: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'channel_04_out' }),
            isCausal: true,
        }),
        deafen: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'deafen_1' }),
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
        mute: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'mute_1' }),
            isCausal: true,
        }),
        newMessage: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'dm_02' }),
            isCausal: true,
        }),
        pushToTalkOn: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'ptt_push_3' }),
            isCausal: true,
        }),
        pushToTalkOff: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'ptt_release_3' }),
            isCausal: true,
        }),
        screenSharing: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'share_02' }),
            isCausal: true,
        }),
        unDeafen: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'undeafen_1' }),
            isCausal: true,
        }),
        unMute: one2one('mail.sound_effect', {
            default: insertAndReplace({ filename: 'unmute_1' }),
            isCausal: true,
        }),
    };
    SoundEffects.identifyingFields = ['messaging'];
    SoundEffects.modelName = 'mail.sound_effects';

    return SoundEffects;
}

registerNewModel('mail.sound_effects', factory);
