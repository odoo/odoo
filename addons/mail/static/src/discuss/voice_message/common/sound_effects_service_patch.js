/* @odoo-module */

import { SoundEffects } from "@mail/core/common/sound_effects_service";
import { patch } from "@web/core/utils/patch";

patch(SoundEffects.prototype, "discuss/voice_message/common", {
    setup() {
        this._super(...arguments);
        this.activeAnalyser = null;
    },
    /**
     * handle stop and start on voice messages
     * @param {import("@mail/discuss/voice_message/voice_analyser").VoiceAnalyser} voiceAnalyser
     */
    onClickAnalyser(voiceAnalyser) {
        if (
            this.activeAnalyser &&
            this.activeAnalyser !== voiceAnalyser &&
            this.activeAnalyser.state.playing
        ) {
            this.activeAnalyser.soundEffectsService.onClickAnalyser(this.activeAnalyser);
        }
        this.activeAnalyser = voiceAnalyser;
        if (voiceAnalyser.state.playing) {
            clearInterval(voiceAnalyser.state.intervalId);
            voiceAnalyser.state.paused = true;
            voiceAnalyser.state.playing = false;
            Promise.resolve(voiceAnalyser.audioRef.el.pause()).catch(() => {
                voiceAnalyser.state.playing = true;
                voiceAnalyser.state.paused = false;
            });
            return;
        }

        if (voiceAnalyser.state.paused) {
            voiceAnalyser.startTimer();
            voiceAnalyser.state.playing = true;
            voiceAnalyser.state.paused = false;
            Promise.resolve(voiceAnalyser.audioRef.el.play()).catch(() => {
                voiceAnalyser.state.paused = true;
                voiceAnalyser.state.playing = false;
            });
            requestAnimationFrame(voiceAnalyser.renderFrame.bind(voiceAnalyser));
            return;
        }

        voiceAnalyser.audioRef.el.load();
        if (!voiceAnalyser.analyser) {
            voiceAnalyser.audioContext = new AudioContext();
            var src = voiceAnalyser.audioContext.createMediaElementSource(
                voiceAnalyser.audioRef.el
            );
            voiceAnalyser.analyser = voiceAnalyser.audioContext.createAnalyser();
            src.connect(voiceAnalyser.analyser);
            voiceAnalyser.analyser.connect(voiceAnalyser.audioContext.destination);
            voiceAnalyser.analyser.fftSize = 256;
            var bufferLength = voiceAnalyser.analyser.frequencyBinCount;
            voiceAnalyser.dataArray = new Uint8Array(bufferLength);
        }
        voiceAnalyser.ctx.clearRect(
            0,
            0,
            voiceAnalyser.canvasRef.el.width,
            voiceAnalyser.canvasRef.el.height
        );
        voiceAnalyser.fillBackground();
        requestAnimationFrame(voiceAnalyser.renderFrame.bind(voiceAnalyser));
        voiceAnalyser.startTimer();
        voiceAnalyser.state.playing = true;
        Promise.resolve(voiceAnalyser.audioRef.el.play()).catch(() => {
            voiceAnalyser.state.playing = false;
        });
    },
});
