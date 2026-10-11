import {
    Component,
    computed,
    onMounted,
    onWillUnmount,
    proxy,
    signal,
    types,
    useOnChange,
    useProps,
    useScope,
} from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { clamp } from "@web/core/utils/numbers";
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
    audioRef = signal.ref(HTMLAudioElement);
    drawerRef = signal.ref();
    progressRef = signal.ref(HTMLCanvasElement);
    waveRef = signal.ref(HTMLCanvasElement);
    wrapperRef = signal.ref();

    scope = useScope();

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            attachment: types.instanceOf(this.store["ir.attachment"]),
        });
        this.voiceMessageService = useService("discuss.voice_message");
        this.notification = useService("notification");
        this.state = proxy({
            playing: false,
            repeat: false,
            currentTime: "",
            totalTime: "",
        });
        this.playButton = computed(() => {
            if (this.state.playing) {
                return { icon: "pause", title: _t("Pause") };
            }
            if (this.state.repeat) {
                return { icon: "refresh", title: _t("Replay") };
            }
            return { icon: "play_arrow", title: _t("Play") };
        });
        useOnChange(
            () => [this.props.attachment.voiceMetadata.playbackRate],
            () => this.applyPlaybackRate(),
            { initialRun: false }
        );
        useOnChange(
            () => [this.props.attachment.uploading],
            (uploading) => {
                if (!uploading) {
                    this.loadAudio();
                }
            },
            { initialRun: false }
        );
        onMounted(() => {
            this.initElements();
            this.audioEl = this.audioRef();
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

    /**
     * @param {HTMLCanvasElement} canvas
     * @param {string} color
     * @returns {CanvasRenderingContext2D}
     */
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
        if (this.scope.isDestroyed()) {
            return;
        }
        this.audioUrl = URL.createObjectURL(blob);
        this.audioEl.src = this.audioUrl;
        const audioCtx = new window.AudioContext();
        try {
            const arrayBuffer = await blob.arrayBuffer();
            const buffer = await audioCtx.decodeAudioData(arrayBuffer);
            if (this.scope.isDestroyed()) {
                return;
            }
            this.duration = buffer.duration;
            this.state.totalTime = this.generateTime(buffer.duration);
            this.setVisualTime(0);
            this.onProgress(0);
            this.drawWave(this.getPeaks(buffer));
            this.applyPlaybackRate();
        } finally {
            if (audioCtx.state !== "closed") {
                await audioCtx.close();
            }
        }
    }

    /** @returns {Promise<Blob>} */
    async fetchFile() {
        const audioUrl = url(this.props.attachment.urlRoute, {
            ...this.props.attachment.urlQueryParams,
        });
        const response = await window.fetch(audioUrl);
        if (!response.ok) {
            throw new Error("HTTP error status: " + response.status);
        }
        return response.blob();
    }

    /**
     * @param {AudioBuffer} buffer
     * @returns {number[]} the loudest sample of each bar
     */
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
                max = Math.max(max, Math.abs(channel[j]));
            }
            peaks[i] = max;
        }
        return peaks;
    }

    /** @param {number[]} peaks */
    drawWave(peaks) {
        return window.requestAnimationFrame(() => {
            const path = this.getWavePath(peaks);
            this.waveCtx.fill(path);
            this.progressCtx.fill(path);
        });
    }

    /**
     * @param {number[]} peaks
     * @returns {Path2D}
     */
    getWavePath(peaks) {
        const { width, height } = this.waveCtx.canvas;
        const ratio = width / this.width;
        const maxPeak = Math.max(...peaks) || 1;
        const barWidth = Math.round(BAR_WIDTH * ratio);
        const radius = BAR_RADIUS * ratio;
        // distance between the left edges of consecutive bars evenly distributed across the canvas width.
        const pitch = (width + BAR_GAP * ratio) / peaks.length;
        const path = new Path2D();
        for (let i = 0; i < peaks.length; i++) {
            // Scale each bar relative to the loudest peak, cap it to a fraction of the canvas height,
            // and enforce a minimum height so sections with silence remain visible.
            const barHeight = Math.round(
                Math.max(BAR_MIN_HEIGHT * ratio, (peaks[i] / maxPeak) * height * WAVE_AMPLITUDE)
            );
            const x = Math.round(i * pitch);
            const y = Math.round((height - barHeight) / 2);
            path.roundRect(x, y, barWidth, barHeight, radius);
        }
        return path;
    }

    play() {
        this.voiceMessageService.activePlayer?.pause();
        this.voiceMessageService.activePlayer = this;
        if (this.state.repeat) {
            this.seekTo(0);
        }
        this.state.repeat = false;
        const requestId = ++this.playRequestId;
        this.audioEl
            .play()
            .then(() => {
                if (this.playRequestId !== requestId) {
                    return;
                }
                this.state.playing = true;
                this.trackPlaybackProgress();
            })
            .catch(() => {
                if (this.playRequestId !== requestId) {
                    return;
                }
                if (this.voiceMessageService.activePlayer === this) {
                    this.voiceMessageService.activePlayer = null;
                }
                this.state.playing = false;
            });
    }

    /** @param {{ end?: boolean }} [options] */
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
        this.state.playing = false;
    }

    /** @param {number} progress between 0 and 1 */
    seekTo(progress) {
        this.state.repeat = false;
        const elapsedTime = progress * this.duration;
        this.audioEl.currentTime = elapsedTime;
        this.setVisualTime(elapsedTime);
        this.onProgress(progress);
    }

    trackPlaybackProgress() {
        if (this.scope.isDestroyed()) {
            return;
        }
        const time = this.audioEl.currentTime;
        if (this.state.playing) {
            this.setVisualTime(time);
            this.onProgress(Math.min(time / this.duration, 1));
            window.requestAnimationFrame(() => this.trackPlaybackProgress());
        }
    }

    /** @param {number} progress between 0 and 1 */
    onProgress(progress) {
        // Only update when playback progresses by a visible pixel.
        const position = Math.round(progress * this.width);
        if (position < this.lastPos || position - this.lastPos >= 1) {
            this.lastPos = position;
            this.progressWave.style.width = position + "px";
        }
    }

    applyPlaybackRate() {
        this.audioEl.playbackRate = this.props.attachment.voiceMetadata.playbackRate;
    }

    /** @param {number} timeInSecond */
    setVisualTime(timeInSecond) {
        this.state.currentTime = this.generateTime(timeInSecond);
    }

    /**
     * @param {number} timeInSecond
     * @returns {string} formatted as "mm : ss"
     */
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

    /** @param {MouseEvent} ev */
    onClickWave(ev) {
        if (this.props.attachment.uploading || this.isAudioLoading) {
            return;
        }
        const { left } = this.wrapper.getBoundingClientRect();
        this.seekTo(clamp((ev.clientX - left) / this.wrapper.scrollWidth, 0, 1));
    }

    onClickPlayPause() {
        if (this.props.attachment.uploading || this.isAudioLoading) {
            return;
        }
        if (this.state.playing) {
            this.pause();
        } else {
            this.play();
        }
    }
}
