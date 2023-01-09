/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "SoundEffects",
    fields: {
        channelJoin: one("SoundEffect", {
            default: { defaultVolume: 0.3, path: "/mail/static/src/audio/channel_01_in" },
            isCausal: true,
        }),
        channelLeave: one("SoundEffect", {
            default: { path: "/mail/static/src/audio/channel_04_out" },
            isCausal: true,
        }),
        deafen: one("SoundEffect", {
            default: { defaultVolume: 0.15, path: "/mail/static/src/audio/deafen_new_01" },
            isCausal: true,
        }),
        incomingCall: one("SoundEffect", {
            default: { defaultVolume: 0.15, path: "/mail/static/src/audio/call_02_in_" },
            isCausal: true,
        }),
        memberLeave: one("SoundEffect", {
            default: { defaultVolume: 0.5, path: "/mail/static/src/audio/channel_01_out" },
            isCausal: true,
        }),
        mute: one("SoundEffect", {
            default: { defaultVolume: 0.2, path: "/mail/static/src/audio/mute_1" },
            isCausal: true,
        }),
        newMessage: one("SoundEffect", {
            default: { path: "/mail/static/src/audio/dm_02" },
            isCausal: true,
        }),
        pushToTalkOn: one("SoundEffect", {
            default: { defaultVolume: 0.05, path: "/mail/static/src/audio/ptt_push_1" },
            isCausal: true,
        }),
        pushToTalkOff: one("SoundEffect", {
            default: { defaultVolume: 0.05, path: "/mail/static/src/audio/ptt_release_1" },
            isCausal: true,
        }),
        screenSharing: one("SoundEffect", {
            default: { defaultVolume: 0.5, path: "/mail/static/src/audio/share_02" },
            isCausal: true,
        }),
        undeafen: one("SoundEffect", {
            default: { defaultVolume: 0.15, path: "/mail/static/src/audio/undeafen_new_01" },
            isCausal: true,
        }),
        unmute: one("SoundEffect", {
            default: { defaultVolume: 0.2, path: "/mail/static/src/audio/unmute_1" },
            isCausal: true,
        }),
    },
});
