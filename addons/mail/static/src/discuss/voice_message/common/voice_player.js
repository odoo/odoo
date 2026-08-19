import {
    Component,
    onMounted,
    onWillUnmount,
    proxy,
    signal,
    status,
    types,
    useOnChange,
    useProps,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

// Used to draw the waveform generated for the recorded voice, sizes in pixels.
const BAR_WIDTH = 3;
const BAR_GAP = 2;
const BAR_MIN_HEIGHT = 3;
const BAR_RADIUS = 1.5;
const WAVE_AMPLITUDE = 0.65;
const WAVE_COLOR = "#7775";

export class VoicePlayer extends Component {
    static template = "mail.VoicePlayer";

    /** @type {HTMLAudioElement} */
    audioEl;
    /** @type {string|undefined} */
    audioUrl;
    /** @type {number} */
    barCount;
    duration = 0;
    /** @type {number} */
    height;
    isAudioLoading = false;
    lastPos = 0;
    // Used to ignore the result of a play() call when playback has already stopped.
    playRequestId = 0;
    /** @type {CanvasRenderingContext2D} */
    progressCtx;
    /** @type {HTMLElement} */
    progressWave;
    /** @type {CanvasRenderingContext2D} */
    waveCtx;
    /** @type {number} */
    width;
    /** @type {HTMLElement} */
    wrapper;
    audioRef = signal.ref();
    drawerRef = signal.ref();
    progressRef = signal.ref();
    waveRef = signal.ref();
    wrapperRef = signal.ref();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            attachment: types.instanceOf(this.store["ir.attachment"]),
        });
        /** @type {import("@mail/discuss/voice_message/common/voice_message_service").VoiceMessageService} */
        this.voiceMessageService = useService("discuss.voice_message");
        this.notification = useService("notification");
        this.state = proxy({
            paused: true,
            playing: false,
            repeat: false,
            currentTime: "",
            totalTime: "",
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
            this.audioEl.addEventListener("ended", () => this.pause({ end: true }));
            this.wrapper.addEventListener("click", (e) => {
                e.stopPropagation();
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

    get playIcon() {
        if (this.state.playing) {
            return "pause";
        }
        return this.state.repeat ? "refresh" : "play_arrow";
    }

    get playTitle() {
        if (this.state.playing) {
            return _t("Pause");
        }
        return this.state.repeat ? _t("Replay") : _t("Play");
    }

    initElements() {
        this.wrapper = this.wrapperRef();
        this.progressWave = this.drawerRef();
        this.width = this.wrapper.clientWidth;
        this.height = this.wrapper.clientHeight;
        // Fill the available width with evenly spaced bars (bar + gap)
        this.barCount = Math.max(1, Math.round((this.width + BAR_GAP) / (BAR_WIDTH + BAR_GAP)));
        this.waveCtx = this.setupCanvas(this.waveRef(), WAVE_COLOR);
        this.progressCtx = this.setupCanvas(
            this.progressRef(),
            getComputedStyle(this.wrapper).getPropertyValue("--primary")
        );
    }

    setupCanvas(canvas, color) {
        const ratio = window.devicePixelRatio || 1;
        // Scale the backing canvas to the device pixel ratio for sharper rendering.
        canvas.width = Math.round(this.width * ratio);
        canvas.height = Math.round(this.height * ratio);
        canvas.style.width = `${this.width}px`;
        canvas.style.height = `${this.height}px`;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = color;
        return ctx;
    }

    loadAudio() {
        if (this.isAudioLoading) {
            return;
        }
        this.isAudioLoading = true;
        return this._loadAudio()
            .catch((err) => {
                console.warn("Voice message audio could not be fetched or decoded.", err);
                this.notification.add(_t("Could not load the voice message."), {
                    type: "warning",
                });
            })
            .finally(() => {
                this.isAudioLoading = false;
            });
    }

    async _loadAudio() {
        this.destroyAudio();
        const blob = await this.fetchFile();
        if (status(this) === "destroyed") {
            return;
        }
        this.audioUrl = URL.createObjectURL(blob);
        this.audioEl.src = this.audioUrl;
        const audioCtx = new browser.AudioContext();
        try {
            const arrayBuffer = await blob.arrayBuffer();
            const buffer = await audioCtx.decodeAudioData(arrayBuffer);
            if (status(this) === "destroyed") {
                return;
            }
            this.duration = buffer.duration;
            this.state.totalTime = this.generateTime(buffer.duration);
            this.setVisualTime(0);
            this.onProgress(0);
            this.drawWave(this.getPeaks(buffer));
            this.applySettings();
        } finally {
            if (audioCtx.state !== "closed") {
                await audioCtx.close();
            }
        }
    }

    async fetchFile() {
        const audioUrl = url(this.props.attachment.urlRoute, {
            ...this.props.attachment.urlQueryParams,
        });
        const response = await browser.fetch(audioUrl);
        if (!response.ok) {
            throw new Error("HTTP error status: " + response.status);
        }
        return response.blob();
    }

    getPeaks(buffer) {
        const peaks = [];
        // Number of audio samples represented by each bar.
        const sampleSize = buffer.length / this.barCount;
        // Sample roughly 10 points per bar instead of every sample.
        // This significantly reduces processing while preserving the visual shape.
        const sampleStep = Math.max(1, Math.floor(sampleSize / 10));
        const channel = buffer.getChannelData(0);
        for (let i = 0; i < this.barCount; i++) {
            const start = Math.floor(i * sampleSize);
            const end = Math.floor(start + sampleSize);
            let max = 0;
            for (let j = start; j < end; j += sampleStep) {
                const value = Math.abs(channel[j]);
                if (value > max) {
                    max = value;
                }
            }
            peaks[i] = max;
        }
        return peaks;
    }

    drawWave(peaks) {
        return browser.requestAnimationFrame(() => {
            this.drawLineToContext(this.waveCtx, peaks);
            this.drawLineToContext(this.progressCtx, peaks);
        });
    }

    drawLineToContext(ctx, peaks) {
        const { width, height } = ctx.canvas;
        const ratio = width / this.width;
        const maxPeak = Math.max(...peaks) || 1;
        const barWidth = Math.round(BAR_WIDTH * ratio);
        const radius = BAR_RADIUS * ratio;
        // distance between the left edges of consecutive bars evenly distributed across the canvas width.
        const pitch = (width + BAR_GAP * ratio) / peaks.length;
        ctx.beginPath();
        for (let i = 0; i < peaks.length; i++) {
            // Scale each bar relative to the loudest peak, cap it to a fraction of the canvas height,
            // and enforce a minimum height so sections with silence remain visible.
            const barHeight = Math.round(
                Math.max(BAR_MIN_HEIGHT * ratio, (peaks[i] / maxPeak) * height * WAVE_AMPLITUDE)
            );
            const x = Math.round(i * pitch);
            const y = Math.round((height - barHeight) / 2);
            ctx.roundRect(x, y, barWidth, barHeight, radius);
        }
        ctx.fill();
    }

    play() {
        this.voiceMessageService.activePlayer?.pause();
        this.voiceMessageService.activePlayer = this;
        if (this.state.repeat) {
            this.seekTo(0);
        }
        this.state.repeat = false;
        this.applySettings();
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
                if (this.voiceMessageService.activePlayer === this) {
                    this.voiceMessageService.activePlayer = null;
                }
                this.state.paused = true;
                this.state.playing = false;
            });
    }

    pause(options) {
        this.playRequestId++;
        if (this.voiceMessageService.activePlayer === this) {
            this.voiceMessageService.activePlayer = null;
        }
        if (options?.end) {
            this.state.repeat = true;
            this.setVisualTime(this.duration);
            this.onProgress(1);
        }
        this.audioEl.pause();
        this.state.paused = true;
        this.state.playing = false;
    }

    seekTo(progress) {
        this.state.repeat = false;
        const elapsedTime = progress * this.duration;
        this.audioEl.currentTime = elapsedTime;
        this.setVisualTime(elapsedTime);
        this.onProgress(progress);
    }

    trackPlaybackProgress() {
        if (status(this) === "destroyed") {
            return;
        }
        const time = this.audioEl.currentTime;
        if (this.state.playing) {
            this.setVisualTime(time);
            this.onProgress(Math.min(time / this.duration, 1));
            browser.requestAnimationFrame(() => this.trackPlaybackProgress());
        }
    }

    onProgress(progress) {
        // Only update when playback progresses by a visible pixel.
        const position = Math.round(progress * this.width);
        if (position < this.lastPos || position - this.lastPos >= 1) {
            this.lastPos = position;
            this.progressWave.style.width = position + "px";
        }
    }

    applySettings() {
        const { voiceMetadata } = this.props.attachment;
        this.audioEl.playbackRate = voiceMetadata.playbackRate;
    }

    setVisualTime(timeInSecond) {
        this.state.currentTime = this.generateTime(timeInSecond);
    }

    generateTime(timeInSecond) {
        const second = Math.floor(timeInSecond % 60);
        const minute = Math.floor(timeInSecond / 60);
        return `${String(minute).padStart(2, "0")} : ${String(second).padStart(2, "0")}`;
    }

    destroyAudio() {
        this.playRequestId++;
        this.audioEl.pause();
        this.audioEl.removeAttribute("src");
        this.audioEl.load();
        this.state.paused = true;
        this.state.playing = false;
        if (this.audioUrl) {
            URL.revokeObjectURL(this.audioUrl);
            this.audioUrl = "";
        }
        this.duration = 0;
        this.state.currentTime = "";
        this.state.totalTime = "";
        this.lastPos = 0;
        this.progressWave.style.width = "0px";
        for (const ctx of [this.waveCtx, this.progressCtx]) {
            ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
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
