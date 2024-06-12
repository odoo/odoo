/* @odoo-module */
import {
    Component,
    useState,
    onMounted,
    onWillUnmount,
    useEffect,
    useRef,
    status,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

const WAVE_COLOR = "#7775";

/**
 * @typedef {Object} Props
 * @property {import("models").Attachment} attachment
 * @extends {Component<Props, Env>}
 */
export class VoicePlayer extends Component {
    static props = ["attachment"];
    static template = "mail.VoicePlayer";

    /** @type {number} */
    lastPlaytime = 0;
    /** @type {number} */
    lastPos = 0;
    /** @type {number} */
    startPosition = 0;
    /** @type {string} */
    progressColor;
    /** @type {GainNode} */
    gainNode;
    /** @type {AudioContext} */
    audioCtx;
    scheduledPause;
    /** @type {AudioBuffer} */
    buffer;
    /** @type {AnalyserNode} */
    analyser;
    /** @type {AudioBufferSourceNode} */
    source;
    /** @type {number} */
    width;
    /** @type {number} */
    height;
    /** @type {HTMLElement} */
    wrapper;
    /** @type {HTMLElement} */
    progressWave;
    /** @type {CanvasRenderingContext2D} */
    waveCtx;
    /** @type {CanvasRenderingContext2D} */
    progressCtx;

    setup() {
        this.wrapperRef = useRef("wrapper");
        this.drawerRef = useRef("drawer");
        this.waveRef = useRef("wave");
        this.progressRef = useRef("progress");
        /** @type {import("@mail/discuss/voice_message/common/voice_message_service").VoiceMessageService} */
        this.voiceMessageService = useService("discuss.voice_message");
        this.state = useState({
            paused: true,
            playing: false,
            repeat: false,
            visualTime: "-- : --",
        });
        useEffect(
            (playing) => {
                if (playing) {
                    this.addOnAudioProcess();
                }
            },
            () => [this.state.playing]
        );
        useEffect(
            (uploading) => {
                if (uploading) {
                    return;
                }
                if (this.wasUploading && !uploading) {
                    this.makeAudio();
                }
                this.wasUploading = uploading;
            },
            () => [this.props.attachment.uploading]
        );
        onMounted(() => {
            this.initElements();
            this.wrapper.addEventListener("click", (e) => {
                if (this.props.attachment.uploading) {
                    return;
                }
                const clientX = (e.targetTouches ? e.targetTouches[0] : e).clientX;
                const bcr = this.wrapper.getBoundingClientRect();
                const progressPixels = clientX - bcr.left;
                const progress = Math.min(
                    Math.max(0, progressPixels / this.wrapper.scrollWidth),
                    1
                );
                this.seekTo(progress);
            });
            if (!this.props.attachment.uploading) {
                this.makeAudio();
            }
            this.wasUploading = this.props.attachment.uploading;
        });
        onWillUnmount(() => {
            if (this.state.playing) {
                this.pause();
            }
            this.destroyWebAudio();
        });
    }

    makeAudio() {
        this.audioCtx = new browser.AudioContext();
        this.gainNode = this.audioCtx.createGain();
        this.gainNode.connect(this.audioCtx.destination);
        this.analyser = this.audioCtx.createAnalyser();
        this.analyser.connect(this.gainNode);
        this.fetchFile(
            url(this.props.attachment.urlRoute, {
                ...this.props.attachment.urlQueryParams,
            })
        ).then((arrayBuffer) => this.drawBuffer(arrayBuffer));
    }

    async fetchFile(url) {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error("HTTP error status: " + response.status);
        }
        const arrayBuffer = await response.arrayBuffer();
        return arrayBuffer;
    }

    getPlayedTime() {
        return this.audioCtx.currentTime - this.lastPlaytime;
    }

    getCurrentTime() {
        if (this.state.paused) {
            return this.startPosition;
        } else {
            return this.startPosition + this.getPlayedTime();
        }
    }

    play() {
        if (this.voiceMessageService.activePlayer) {
            this.voiceMessageService.activePlayer.pause();
        }
        this.voiceMessageService.activePlayer = this;
        this.state.repeat = false;
        this.createSource();
        const { start, end } = this.seekToElapsed();
        this.scheduledPause = end;
        this.source.start(0, start);
        this.state.playing = true;
        this.state.paused = false;
    }

    pause(options) {
        this.voiceMessageService.activePlayer = null;
        if (options?.end) {
            this.state.repeat = true;
        }
        this.scheduledPause = null;
        this.startPosition += this.getPlayedTime();
        if (this.source) {
            try {
                this.source.stop();
            } catch (e) {
                if (e.name === "InvalidStateError") {
                    return;
                }
                throw e;
            }
        }
        if (!options?.continue) {
            this.state.paused = true;
            this.state.playing = false;
        }
    }

    getPeaks() {
        const peaks = [];
        const sampleSize = this.buffer.length / this.width;
        const sampleStep = Math.floor(sampleSize / 10);
        const chan = this.buffer.getChannelData(0);
        let i;
        for (i = 0; i < this.width; i++) {
            const start = Math.floor(i * sampleSize);
            const end = Math.floor(start + sampleSize);
            let min = chan[start];
            let max = min;
            let j;
            for (j = start; j < end; j += sampleStep) {
                const value = chan[j];
                if (value > max) {
                    max = value;
                }
                if (value < min) {
                    min = value;
                }
            }
            peaks[i] = max;
        }
        return peaks;
    }

    createSource() {
        this.source?.disconnect();
        this.source = this.audioCtx.createBufferSource();
        this.source.buffer = this.buffer;
        this.source.connect(this.analyser);
    }

    /**
     * @param {number} [start] float representing start time
     * @param {number} [end] float representing end time
     * @returns {Object} res
     * @returns {number} res.start
     * @returns {number} res.end
     */
    seekToElapsed(start, end) {
        this.scheduledPause = null;
        if (start === undefined) {
            start = this.getCurrentTime();
            if (start >= this.buffer.duration) {
                start = 0;
            }
        }
        if (end === undefined) {
            end = this.buffer.duration;
        }
        this.startPosition = start;
        this.lastPlaytime = this.audioCtx.currentTime;
        return { start, end };
    }

    onProgress(progress) {
        const position = Math.round(progress * this.width);
        if (position < this.lastPos || position - this.lastPos >= 1) {
            this.lastPos = position;
            this.progressWave.style.width = position + "px";
        }
    }

    seekTo(progress) {
        if (this.state.playing) {
            this.pause({ continue: true });
        }
        this.state.repeat = false;
        const elapsedTime = progress * this.buffer.duration;
        this.state.visualTime = this.generateTime(Math.floor(elapsedTime));
        this.seekToElapsed(elapsedTime);
        this.onProgress(progress);
        if (this.state.playing) {
            this.play();
        }
    }

    async drawBuffer(arrayBuffer) {
        const buffer = await this.audioCtx.decodeAudioData(arrayBuffer);
        this.state.visualTime = this.generateTime(Math.floor(buffer.duration));
        this.startPosition = 0;
        this.lastPlaytime = this.audioCtx.currentTime;
        this.buffer = buffer;
        this.createSource();
        this.drawWave(this.getPeaks());
    }

    async destroyWebAudio() {
        this.source?.disconnect();
        this.gainNode?.disconnect();
        this.analyser?.disconnect();
        try {
            await this.audioCtx?.close();
        } catch (e) {
            if (e.name === "InvalidStateError") {
                return;
            }
            throw e;
        }
    }

    addOnAudioProcess() {
        if (status(this) === "destroyed") {
            return;
        }
        const time = this.getCurrentTime();
        if (time >= this.scheduledPause && this.state.playing) {
            this.pause({ end: true });
        } else if (this.state.playing) {
            this.state.visualTime = this.generateTime(Math.floor(time));
            const playedPercents = this.getCurrentTime() / this.buffer.duration;
            this.onProgress(playedPercents);
            requestAnimationFrame(() => this.addOnAudioProcess());
        }
    }

    generateTime(timeInSecond) {
        const second = timeInSecond % 60;
        const minute = Math.floor(timeInSecond / 60);
        return (
            (minute < 10 ? "0" + minute : minute) + " : " + (second < 10 ? "0" + second : second)
        );
    }

    initElements() {
        this.wrapper = this.wrapperRef.el;
        this.progressWave = this.drawerRef.el;
        this.progressColor = getComputedStyle(this.wrapper).getPropertyValue("--primary");
        this.width = this.wrapper.clientWidth;
        this.height = this.wrapper.clientHeight;

        const wave = this.waveRef.el;
        wave.width = this.width;
        wave.height = this.height;
        this.waveCtx = wave.getContext("2d");
        this.waveCtx.fillStyle = WAVE_COLOR;

        const progress = this.progressRef.el;
        progress.width = this.width;
        progress.height = this.height;
        this.progressCtx = progress.getContext("2d");
        this.progressCtx.fillStyle = this.progressColor;
    }

    drawWave(peaks) {
        return requestAnimationFrame(() => {
            this.drawLines(peaks);
            this.fillRect(0, this.height / 2, this.width, 0.5);
        });
    }

    fillRect(x, y, width, height) {
        const intersection = {
            x1: x,
            y1: y,
            x2: x + width,
            y2: y + height,
        };
        if (intersection.x1 < intersection.x2) {
            this.fillRects(
                intersection.x1,
                intersection.y1,
                intersection.x2 - intersection.x1,
                intersection.y2 - intersection.y1
            );
        }
    }

    fillRects(x, y, width, height) {
        this.waveCtx.fillRect(x, y, width, height);
        this.progressCtx.fillRect(x, y, width, height);
    }

    drawLines(peaks) {
        this.drawLineToContext(this.waveCtx, peaks);
        this.drawLineToContext(this.progressCtx, peaks);
    }

    drawLineToContext(ctx, peaks) {
        const maxPeak = Math.max(...peaks);
        let i, peak;
        for (i = 0; i <= peaks.length; i++) {
            peak = peaks[i];
            const h = (peak * this.height) / maxPeak;
            ctx.fillRect(i, (this.height - h) / 2, 1.5, h);
        }
    }

    onClickPlayPause() {
        if (this.props.attachment.uploading) {
            return;
        }
        if (this.state.paused) {
            this.play();
        } else {
            this.pause();
        }
    }
}
