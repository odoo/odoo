import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { url } from "@web/core/utils/urls";
import { Deferred } from "@web/core/utils/concurrency";

const WAIT_IN_QUEUE_DURATION = 800;

function stopEffect(soundEffect) {
    if (!soundEffect) {
        return;
    }
    clearTimeout(soundEffect.queueTimeout);
    if (soundEffect.audio) {
        soundEffect.audio.pause();
        soundEffect.audio.currentTime = 0;
    }
}

export class SoundEffects {
    /**
     * @param {import("@web/env").OdooEnv} env
     */
    constructor(env) {
        this.soundEffects = {
            "call-join": { defaultVolume: 0.75, path: "/mail/static/src/audio/call-join" },
            "call-leave": { defaultVolume: 0.75, path: "/mail/static/src/audio/call-leave" },
            "earphone-off": { defaultVolume: 0.15, path: "/mail/static/src/audio/earphone-off" },
            "earphone-on": { defaultVolume: 0.15, path: "/mail/static/src/audio/earphone-on" },
            "mic-off": { defaultVolume: 0.2, path: "/mail/static/src/audio/mic-off" },
            "mic-on": { defaultVolume: 0.2, path: "/mail/static/src/audio/mic-on" },
            "ptt-press": { defaultVolume: 0.1, path: "/mail/static/src/audio/ptt-press" },
            "ptt-release": { defaultVolume: 0.1, path: "/mail/static/src/audio/ptt-release" },
            "call-invitation": {
                lockDuration: WAIT_IN_QUEUE_DURATION + 200,
                defaultVolume: 0.5,
                path: "/mail/static/src/audio/call-invitation",
            },
            "new-message": { defaultVolume: 1, path: "/mail/static/src/audio/new-message" },
            "screen-sharing": {
                defaultVolume: 0.75,
                path: "/mail/static/src/audio/screen-sharing",
            },
            "member-leave": { defaultVolume: 0.5, path: "/mail/static/src/audio/channel_01_out" },
        };
    }

    /**
     * @param {String} soundEffectName
     * @param {Object} [param1]
     * @param {boolean} [param1.loop] true if we want to make the audio loop, will only stop if stop() is called
     * @param {float} [param1.volume] the volume percentage in decimal to play this sound.
     *   If not provided, uses the default volume of this sound effect.
     * @param {string | number} [param1.unique] an unique identifier if the same sound effect should have distinct locks
     */
    play(soundEffectName, { loop = false, volume, unique } = {}) {
        if (typeof browser.Audio === "undefined") {
            return;
        }
        const soundEffect = this.soundEffects[soundEffectName];
        if (!soundEffect) {
            return;
        }
        const controller = new AbortController();
        /**
         * Wait in queue just in case the lock opened early due to a crash, this can happen
         * if the tab that gets the lock is not allowed to play audio.
         */
        soundEffect.queueTimeout = setTimeout(() => controller.abort(), WAIT_IN_QUEUE_DURATION);
        const lockName = unique ? `${soundEffectName}${unique}` : soundEffectName;
        navigator.locks
            .request(lockName, { signal: controller.signal }, async () => {
                if (!soundEffect.audio) {
                    const audio = new browser.Audio();
                    const ext = audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
                    this._setAudioSrc(audio, url(soundEffect.path + ext));
                    soundEffect.audio = audio;
                }
                const lockTime = new Deferred();
                setTimeout(lockTime.resolve, soundEffect.lockDuration ?? 0);
                if (!soundEffect.audio.paused) {
                    if (loop && soundEffect.audio.loop) {
                        await lockTime;
                        return;
                    }
                    soundEffect.audio.pause();
                }
                soundEffect.audio.currentTime = 0;
                soundEffect.audio.loop = loop;
                soundEffect.audio.volume = volume ?? soundEffect.defaultVolume ?? 1;
                const audioProm = Promise.resolve(soundEffect.audio.play());
                await Promise.allSettled([
                    /**
                     * Skipping the lock in case of failure so that other callers
                     * in queue can attempt to play the sound.
                     */
                    audioProm.catch(() => lockTime.reject()),
                    lockTime,
                ]);
                clearTimeout(soundEffect.queueTimeout);
            })
            .catch(() => {});
    }
    /** To be patched in tests to use data-src */
    _setAudioSrc(audio, srcPath) {
        audio.src = srcPath;
    }
    /**
     * Resets the audio to the start of the track and pauses it.
     * @param {String} [soundEffectName]
     */
    stop(soundEffectName) {
        if (soundEffectName) {
            const soundEffect = this.soundEffects[soundEffectName];
            stopEffect(soundEffect);
        } else {
            for (const soundEffect of Object.values(this.soundEffects)) {
                stopEffect(soundEffect);
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
