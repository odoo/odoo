/* @odoo-module */
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @property {import("@mail/attachments/attachment_model").Attachment} attachment
 * @extends {Component<Props, Env>}
 */
export class VoiceAnalyser extends Component {
    static props = ["attachment"];
    static template = "mail.VoiceAnalyser";

    duration;
    dataArray;
    startTime;
    analyser;
    pausedElapsed = 0;
    intervalId;

    setup() {
        /** @type {import("@mail/core/common/sound_effects_service").SoundEffects} */
        this.soundEffectsService = useService("mail.sound_effects");
        this.audioRef = useRef("audio");
        this.canvasRef = useRef("canvas");
        this.duration = this.props.attachment.duration;
        this.state = useState({
            playing: false,
            paused: false,
            intervalId: false,
            visualTime: this.generateTime(Math.floor(this.duration / 1000)),
        });

        onMounted(async () => {
            this.primaryColor = getComputedStyle(this.audioRef.el).getPropertyValue("--primary");
            this.ctx = this.canvasRef.el.getContext("2d");
            this.ctx.fillStyle = this.primaryColor;
            this.fillBackground();
        });
        onWillUnmount(() => {
            this.state.playing = false;
            this.closeContext();
            this.analyser?.disconnect();
            clearInterval(this.state.intervalId);
        });
    }

    fillBackground() {
        for (var i = 0; i < this.canvasRef.el.width; i += 6) {
            this.ctx.beginPath();
            this.ctx.arc(i, this.canvasRef.el.height / 2, 2, 0, 2 * Math.PI);
            this.ctx.fill();
        }
    }

    renderFrame(t) {
        if (!this.canvasRef.el) {
            return;
        }
        if (this.state.paused && this.startTime) {
            this.pausedElapsed = t - this.startTime;
            return;
        }
        if (!this.startTime) {
            this.startTime = t;
        } else if (this.pausedElapsed) {
            this.startTime = t - this.pausedElapsed;
            this.pausedElapsed = 0;
        }
        const elapsed = t - this.startTime;
        this.analyser.getByteFrequencyData(this.dataArray);

        const max = Math.max(...this.dataArray);
        const barHeight = (max / 256) * this.canvasRef.el.height;
        const x = (elapsed / this.duration) * this.canvasRef.el.width;
        this.ctx.fillRect(x, (this.canvasRef.el.height - barHeight) / 2, 1, barHeight);

        if (elapsed < this.duration) {
            requestAnimationFrame(this.renderFrame.bind(this));
        } else {
            this.state.playing = false;
            this.startTime = false;
            clearInterval(this.state.intervalId);
            this.soundEffectsService.activeAnalyser = null;
            this.state.visualTime = this.generateTime(Math.floor(this.duration / 1000));
        }
    }

    async closeContext() {
        try {
            await this.audioContext?.close();
        } catch (e) {
            if (e.name === "InvalidStateError") {
                return;
            }
            throw e;
        }
    }

    startTimer() {
        let totalSeconds = 0;
        if (this.pausedElapsed) {
            totalSeconds = Math.floor(this.pausedElapsed / 1000);
        }
        this.state.intervalId = setInterval(() => {
            ++totalSeconds;
            this.state.visualTime = this.generateTime(totalSeconds);
        }, 1000);
    }

    generateTime(timeInSecond) {
        const second = timeInSecond % 60;
        const minute = Math.floor(timeInSecond / 60) % 60;
        return (
            (minute < 10 ? "0" + minute : minute) + " : " + (second < 10 ? "0" + second : second)
        );
    }
}
