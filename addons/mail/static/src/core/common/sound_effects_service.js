import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";

export class SoundEffects {
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    constructor(env) {
        this.soundEffects = {
            "channel-join": { defaultVolume: 0.3, path: "/mail/static/src/audio/channel_01_in" },
            "channel-leave": { path: "/mail/static/src/audio/channel_04_out" },
            deafen: { defaultVolume: 0.15, path: "/mail/static/src/audio/deafen_new_01" },
            "incoming-call": { defaultVolume: 0.15, path: "/mail/static/src/audio/call_02_in_" },
            "member-leave": { defaultVolume: 0.5, path: "/mail/static/src/audio/channel_01_out" },
            mute: { defaultVolume: 0.2, path: "/mail/static/src/audio/mute_1" },
            "new-message": { path: "/mail/static/src/audio/dm_02" },
            "push-to-talk-on": { defaultVolume: 0.05, path: "/mail/static/src/audio/ptt_push_1" },
            "push-to-talk-off": {
                defaultVolume: 0.05,
                path: "/mail/static/src/audio/ptt_release_1",
            },
            "screen-sharing": { defaultVolume: 0.5, path: "/mail/static/src/audio/share_02" },
            undeafen: { defaultVolume: 0.15, path: "/mail/static/src/audio/undeafen_new_01" },
            unmute: { defaultVolume: 0.2, path: "/mail/static/src/audio/unmute_1" },
        };
    }

    /**
     * @param {String} param0 soundEffectName
     * @param {Object} param1
     * @param {boolean} [param1.loop] true if we want to make the audio loop, will only stop if stop() is called
     * @param {float} [param1.volume] the volume percentage in decimal to play this sound.
     *   If not provided, uses the default volume of this sound effect.
     */
    play(soundEffectName, { loop = false, volume } = {}) {
        if (typeof browser.Audio === "undefined") {
            return;
        }
        const soundEffect = this.soundEffects[soundEffectName];
        if (!soundEffect) {
            return;
        }
        if (!soundEffect.audio) {
            const audio = new browser.Audio();
            const ext = audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
            audio.src = url(soundEffect.path + ext);
            soundEffect.audio = audio;
        }
        if (!soundEffect.audio.paused) {
            soundEffect.audio.pause();
        }
        soundEffect.audio.currentTime = 0;
        soundEffect.audio.loop = loop;
        soundEffect.audio.volume = volume ?? soundEffect.defaultVolume ?? 1;
        Promise.resolve(soundEffect.audio.play()).catch(() => {});
    }
    /**
     * Resets the audio to the start of the track and pauses it.
     * @param {String} [soundEffectName]
     */
    stop(soundEffectName) {
        const soundEffect = this.soundEffects[soundEffectName];
        if (soundEffect) {
            if (soundEffect.audio) {
                soundEffect.audio.pause();
                soundEffect.audio.currentTime = 0;
            }
        } else {
            for (const soundEffect of Object.values(this.soundEffects)) {
                if (soundEffect.audio) {
                    soundEffect.audio.pause();
                    soundEffect.audio.currentTime = 0;
                }
            }
        }
    }
}

export const soundEffects = {
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    start(env) {
        return new SoundEffects(env);
    },
};

registry.category("services").add("mail.sound_effects", soundEffects);
