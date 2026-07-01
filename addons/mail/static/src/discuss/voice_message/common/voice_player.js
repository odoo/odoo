import { useOnChange } from "@mail/utils/common/hooks";
import {
    Component,
    onMounted,
    onWillUnmount,
    props,
    proxy,
    signal,
    status,
    types,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";
import { useRef } from "@web/owl2/utils";

const WAVE_COLOR = "#7775";

export class VoicePlayer extends Component {
    static template = "mail.VoicePlayer";

    /** @type {number} */
    playRequestId = 0;
    /** @type {number} */
    lastPos = 0;
    /** @type {string} */
    progressColor;
    /** @type {number} */
    duration = 0;
    /** @type {boolean} */
    isAudioLoading = false;
    /** @type {string} */
    audioUrl;
    /** @type {number[]} */
    peaks;
    /** @type {number} */
    width;
    /** @type {number} */
    height;
    /** @type {HTMLElement} */
    wrapper;
    /** @type {HTMLElement} */
    progressWave;
    /** @type {HTMLAudioElement} */
    audioEl;
    /** @type {CanvasRenderingContext2D} */
    waveCtx;
    /** @type {CanvasRenderingContext2D} */
    progressCtx;

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = props({
            attachment: types.instanceOf(this.store["ir.attachment"].Class),
        });
        this.wrapperRef = useRef("wrapper");
        this.drawerRef = useRef("drawer");
        this.waveRef = useRef("wave");
        this.progressRef = useRef("progress");
        this.audioRef = signal(null);
        /** @type {import("@mail/discuss/voice_message/common/voice_message_service").VoiceMessageService} */
        this.voiceMessageService = useService("discuss.voice_message");
        this.notification = useService("notification");
        this.state = proxy({
            paused: true,
            playing: false,
            repeat: false,
            visualTime: "-- : --",
        });
        useOnChange(
            () => [this.props.attachment.uploading],
            () => {
                if (!this.props.attachment.uploading) {
                    this.loadAudio();
                }
            },
            { initialRun: false }
        );
        onMounted(() => {
            this.initElements();
            this.audioEl = this.audioRef();
            this.wrapper.addEventListener("click", (e) => {
                if (this.props.attachment.uploading || this.isAudioLoading) {
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
                this.loadAudio();
            }
        });
        onWillUnmount(() => {
            if (this.state.playing) {
                this.pause();
            }
            this.destroyAudio();
        });
    }

    loadAudio() {
        if (this.isAudioLoading) {
            return;
        }
        this.isAudioLoading = true;
        return this._loadAudio()
            .catch((err) => {
                this.notification.add(err?.message, { type: "warning" });
            })
            .finally(() => {
                this.isAudioLoading = false;
            });
    }

    async _loadAudio() {
        this.destroyAudio();
        const blob = await this.fetchFile();
        const audioUrl = URL.createObjectURL(blob);
        this.audioUrl = audioUrl;
        if (this.audioEl) {
            this.audioEl.src = audioUrl;
        }
        const audioCtx = new browser.AudioContext();
        try {
            const arrayBuffer = await blob.arrayBuffer();
            const buffer = await audioCtx.decodeAudioData(arrayBuffer);
            this.duration = buffer.duration;
            this.state.visualTime = this.generateTime(Math.floor(buffer.duration));
            this.peaks = this.getPeaks(buffer);
            this.onProgress(0);
            this.drawWave(this.peaks);
            this.applyPlaybackRate();
        } finally {
            try {
                await audioCtx.close();
            } catch (err) {
                if (err.name !== "InvalidStateError") {
                    this.notification.add(err?.message, { type: "warning" });
                }
            }
        }
    }

    async fetchFile() {
        const audioUrl = url(this.props.attachment.urlRoute, {
            ...this.props.attachment.urlQueryParams,
        });
        const response = await fetch(audioUrl);
        if (!response.ok) {
            throw new Error("HTTP error status: " + response.status);
        }
        return response.blob();
    }

    applyPlaybackRate() {
        if (this.audioEl) {
            this.audioEl.playbackRate = this.props.attachment.voice_ids?.[0]?.playbackRate ?? 1;
        }
    }

    play() {
        this.voiceMessageService.activePlayer?.pause();
        this.voiceMessageService.activePlayer = this;
        this.state.repeat = false;
        this.applyPlaybackRate();
        const requestId = ++this.playRequestId;
        this.audioEl
            .play()
            .then(() => {
                if (this.playRequestId !== requestId) {
                    return;
                }
                this.state.playing = true;
                this.state.paused = false;
                this.trackPlaybackProgress();
            })
            .catch(() => {
                if (this.playRequestId !== requestId) {
                    return;
                }
                this.voiceMessageService.activePlayer = null;
                this.state.paused = true;
                this.state.playing = false;
            });
    }

    pause(options) {
        this.playRequestId += 1;
        this.voiceMessageService.activePlayer = null;
        if (options?.end) {
            this.state.repeat = true;
            this.state.visualTime = this.generateTime(Math.floor(this.duration));
            this.onProgress(1);
        }
        this.audioEl?.pause();
        if (!options?.continue) {
            this.state.paused = true;
            this.state.playing = false;
        }
    }

    getPeaks(buffer) {
        const peaks = [];
        const sampleSize = buffer.length / this.width;
        const sampleStep = Math.floor(sampleSize / 10);
        const chan = buffer.getChannelData(0);
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

    onProgress(progress) {
        const position = Math.round(progress * this.width);
        if (position < this.lastPos || position - this.lastPos >= 1) {
            this.lastPos = position;
            this.progressWave.style.width = position + "px";
        }
    }

    seekTo(progress) {
        this.state.repeat = false;
        const elapsedTime = progress * this.duration;
        this.audioEl.currentTime = elapsedTime;
        this.state.visualTime = this.generateTime(Math.floor(elapsedTime));
        this.onProgress(progress);
    }

    destroyAudio() {
        this.playRequestId += 1;
        this.audioEl?.pause();
        if (this.audioEl) {
            this.audioEl.removeAttribute("src");
            this.audioEl.load();
        }
        this.state.paused = true;
        this.state.playing = false;
        if (this.audioUrl) {
            URL.revokeObjectURL(this.audioUrl);
            this.audioUrl = "";
        }
        this.duration = 0;
        this.peaks = null;
        this.lastPos = 0;
        if (this.progressWave) {
            this.progressWave.style.width = "0px";
        }
        if (this.waveCtx && this.progressCtx && this.width && this.height) {
            this.waveCtx.clearRect(0, 0, this.width, this.height);
            this.progressCtx.clearRect(0, 0, this.width, this.height);
        }
    }

    trackPlaybackProgress() {
        if (status(this) === "destroyed") {
            return;
        }
        const time = this.audioEl?.currentTime ?? 0;
        if (time >= this.duration && this.state.playing) {
            this.pause({ end: true });
        } else if (this.state.playing) {
            this.state.visualTime = this.generateTime(Math.floor(time));
            const playedPercents = time / this.duration;
            this.onProgress(playedPercents);
            requestAnimationFrame(() => this.trackPlaybackProgress());
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
        if (this.props.attachment.uploading || this.isAudioLoading) {
            return;
        }
        if (this.state.paused) {
            this.play();
        } else {
            this.pause();
        }
    }
}
