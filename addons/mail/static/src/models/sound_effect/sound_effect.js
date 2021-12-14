/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'SoundEffect',
    identifyingFields: ['path', 'filename'],
    recordMethods: {
        /**
         * @param {Object} param0
         * @param {boolean} [param0.loop] true if we want to make the audio loop, will only stop if stop() is called
         * @param {boolean} [param0.volume]
         */
        play({ loop = false, volume = 1 } = {}) {
            if (typeof(Audio) === "undefined") {
                return;
            }
            if (!this.audio) {
                const audio = new window.Audio();
                const ext = audio.canPlayType("audio/ogg; codecs=vorbis") ? ".ogg" : ".mp3";
                audio.src = this.path + this.filename + ext;
                this.update({ audio });
            }
            this.audio.pause();
            this.audio.currentTime = 0;
            this.audio.loop = loop;
            this.audio.volume = volume;
            Promise.resolve(this.audio.play()).catch(()=>{});
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
         * Name of the audio file.
         */
        filename: attr({
            readonly: true,
            required: true,
        }),
        /**
         * Path to the audio file.
         */
        path: attr({
            default: '/mail/static/src/audio/',
            readonly: true,
            required: true,
        }),
    },
});
