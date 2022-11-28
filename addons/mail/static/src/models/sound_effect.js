/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'SoundEffect',
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
            if (typeof(Audio) === "undefined") {
                return;
            }
            if (!this.audio) {
                const audio = new window.Audio();
                this.update({ audio });
                audio.src = this.source;
            }
            this.audio.pause();
            this.audio.currentTime = 0;
            this.audio.loop = loop;
            this.audio.volume = volume !== undefined ? volume : this.defaultVolume;
            Promise.resolve(this.audio.play()).catch(e => this._onAudioPlayError(e));
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
        /**
         * @private
         * @param {DOMException} error
         */
        _onAudioPlayError(error) {
            if (!this.exists()) {
                return;
            }
            this.update({ audioPlayError: error });
            // error on play can trigger fallback to .mp3; retry in case this
            // solved the problem.
            Promise.resolve(this.audio.play()).catch(() => {});
        },
        /**
         * @private
         */
        _onSourceChanged() {
            if (!this.audio) {
                return;
            }
            this.audio.src = this.source;
            this.audio.load();
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
        audioPlayError: attr(),
        /**
         * The default volume to play this sound effect, when unspecified.
         */
        defaultVolume: attr({
            default: 1,
        }),
        extension: attr({
            compute() {
                if (!this.audio) {
                    return clear();
                }
                // If the device has tried to play audio and failed, perhaps ogg
                // is not supported -> fallback to mp3.
                if (this.audioPlayError && this.audioPlayError.name === 'NotSupportedError') {
                    return '.mp3';
                }
                return this.audio.canPlayType('audio/ogg; codecs=vorbis') ? '.ogg' : '.mp3';
            },
        }),
        /**
         * Name of the audio file.
         */
        filename: attr({
            identifying: true,
        }),
        /**
         * Path to the audio file.
         */
        path: attr({
            default: '/mail/static/src/audio/',
            identifying: true,
        }),
        source: attr({
            compute() {
                if (!this.extension) {
                    return clear();
                }
                return `${this.path}${this.filename}${this.extension}`;
            },
        }),
    },
    onChanges: [
        {
            dependencies: ['source'],
            methodName: '_onSourceChanged',
        },
    ],
});
