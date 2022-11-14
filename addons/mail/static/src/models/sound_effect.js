/** @odoo-module **/

import { attr, Model } from "@mail/model";

Model({
    name: "SoundEffect",
    recordMethods: {
        /**
         * @param {Object} param0
         * @param {boolean} [param0.loop] true if we want to make the audio loop, will only stop if stop() is called
         * @param {float} [param0.volume] the volume percentage in decimal to play this sound.
         *   If not provided, uses the default volume of this sound effect.
         */
        play({ loop = false, volume } = {}) {
            if (this.messaging.isInQUnitTest) {
                return;
            }
            if (typeof Audio === "undefined") {
                return;
            }
            if (!this.audio) {
                const audio = new window.Audio();
                const ext = audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
                audio.src = this.path + ext;
                this.update({ audio });
            }
            this.audio.pause();
            this.audio.currentTime = 0;
            this.audio.loop = loop;
            this.audio.volume = volume !== undefined ? volume : this.defaultVolume;
            Promise.resolve(this.audio.play()).catch(() => {});
        },
        /**
         * Resets the audio to the start of the track and pauses it.
         */
        stop() {
            if (this.audio) {
                this.audio.pause();
                this.audio.currentTime = 0;
            }
        },
    },
    fields: {
        /**
         * HTMLAudioElement
         * Does not require to be mounted on the DOM to operate.
         *
         * Set the first time the audio is played so the file is lazy loaded and
         * then cached.
         */
        audio: attr(),
        /**
         * The default volume to play this sound effect, when unspecified.
         */
        defaultVolume: attr({ default: 1 }),
        /**
         * Path to the audio file.
         */
        path: attr({ identifying: true }),
    },
});
