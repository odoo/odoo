import {
    Component,
    onWillStart,
    onWillUpdateProps,
    onWillUnmount,
    props,
    proxy,
    signal,
    useEffect,
    useListener,
} from "@odoo/owl";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { CallDebriefTimeline } from "@mail/views/fields/call_debrief/call_debrief_timeline";
import { CallDebriefMediaControls } from "@mail/views/fields/call_debrief/call_debrief_media_controls";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

export class CallDebrief extends Component {
    static template = "mail.CallDebrief";
    static components = { CallDebriefTimeline, CallDebriefMediaControls };

    static props = {
        ...standardFieldProps,
        // The name of the field on the record that stores the call's start datetime.
        callStartDateField: { type: String },
        // The name of the field on the record that stores the call's end datetime.
        callEndDateField: { type: String },
    };

    props = props();

    setup() {
        this.callDurationSeconds = 0;
        this.playbackRates = [0.25, 0.5, 0.75, 0.9, 1, 1.25, 1.5, 1.75, 2, 3];
        this.skipNextTimeUpdate = false;
        this.isSwitchingSegment = false;

        this.mediaPlayer = signal(null);
        this.rootElement = signal(null);

        this.orm = useService("orm");
        this.state = proxy({
            currentTime: 0,
            mediaSegments: [],
            currentSegment: undefined,
            error: "",
            isPlaying: false,
            isFullscreen: false,
            playbackRate: 1,
            volume: 1,
            isMuted: false,
            feedback: { icon: "", text: "", id: Date.now() },
        });

        this.onMediaLoadedCallback = null;

        // Tracks active record ID to bypass this.props update lag during async paging
        this.activeResId = this.props.record.resId;

        onWillStart(() => this._loadData(this.props));

        onWillUpdateProps(async (nextProps) => {
            const hasIdChanged = this.props.record.resId !== nextProps.record.resId;
            const hasFieldChanged =
                this.props.record.data[this.props.name] !== nextProps.record.data[nextProps.name];
            if (hasIdChanged || hasFieldChanged) {
                this.activeResId = nextProps.record.resId;
                await this._loadData(nextProps);
            }
        });

        useHotkey("k", () => this.togglePlay(), { global: true });
        useHotkey("space", () => this.togglePlay(), { global: true });
        useHotkey("j", () => { this.seekRelative(-5), this.showMediaControlsFeedback("skip-backward"); }, { global: true, allowRepeat: true });
        useHotkey("l", () => { this.seekRelative(5), this.showMediaControlsFeedback("skip-forward"); }, { global: true, allowRepeat: true });
        useHotkey("arrowleft", () => { this.seekRelative(-5), this.showMediaControlsFeedback("skip-backward"); }, { global: true, allowRepeat: true });
        useHotkey("arrowright", () => { this.seekRelative(5), this.showMediaControlsFeedback("skip-forward"); }, { global: true, allowRepeat: true });
        useHotkey("m", () => { this.toggleMute(); this.showMediaControlsFeedback("mute"); }, { global: true });
        // Supports AZERTY keyboard layouts
        useHotkey("shift+.", () => { this.adjustPlaybackRate(1); this.showMediaControlsFeedback("playback-speed"); }, { global: true });
        useHotkey("shift+?", () => { this.adjustPlaybackRate(-1); this.showMediaControlsFeedback("playback-speed"); }, { global: true });
        // Supports QWERTY keyboard layouts
        useHotkey("shift+>", () => { this.adjustPlaybackRate(1); this.showMediaControlsFeedback("playback-speed"); }, { global: true });
        useHotkey("shift+<", () => { this.adjustPlaybackRate(-1); this.showMediaControlsFeedback("playback-speed"); }, { global: true });
        useHotkey("f", () => { this.toggleFullscreen(); this.showMediaControlsFeedback("fullscreen"); }, { global: true });
        useListener(document, "fullscreenchange", () => {
            this.state.isFullscreen = !!document.fullscreenElement;
        });

        onWillUnmount(() => {
            clearTimeout(this.feedbackTimeout);
        });

        // Effect for hardware media synchronization
        useEffect(() => {
            const media = this.mediaPlayer();
            if (media) {
                media.playbackRate = this.state.playbackRate;
                media.volume = this.state.volume;
                media.muted = this.state.isMuted;
            }
        });
    }

    get hasMedia() {
        return this.state.mediaSegments.length > 0;
    }

    get hasTimeline() {
        return this.hasMedia;
    }

    get hasVideo() {
        return this.state.currentSegment?.type === "video";
    }

    get callDebriefVideoCustomClasses() {
        return {}
    }

    onMediaError() {
        this.showVideoFeedback(_t("Media Error"));
        console.warn("Media playback error. The format might not be supported by your browser.");
    }

    _initCallTiming(start, end) {
        if (!start || !end) {
            this.state.error = _t(
                "CallDebrief widget needs start and end datetime from the parent record."
            );
            this._resetState();
            return false;
        }
        const callStartDate = typeof start === "string" ? deserializeDateTime(start) : start;
        const callEndDate = typeof end === "string" ? deserializeDateTime(end) : end;

        const duration = callEndDate.diff(callStartDate, "seconds").seconds;
        if (duration < 0) {
            this.state.error = _t("Invalid call timing: end date is before start date.");
            this._resetState();
            return false;
        }
        this.callDurationSeconds = duration;
        return true;
    }

    _resetState() {
        this.state.mediaSegments = [];
        this.state.currentSegment = undefined;
        this.state.currentTime = 0;
    }

    async _loadData(props) {
        const initialResId = props.record.resId;
        this.state.error = "";
        this.state.isPlaying = false;
        this.state.currentSegment = undefined;
        this.state.mediaSegments = [];

        const start = props.record.data[props.callStartDateField];
        const end = props.record.data[props.callEndDateField];

        if (!this._initCallTiming(start, end)) {
            return;
        }

        const artifactData = props.record.data[props.name];
        let artifactIds = [];
        if (artifactData && artifactData.currentIds) {
            artifactIds = artifactData.currentIds;
        } else if (Array.isArray(artifactData)) {
            artifactIds = artifactData;
        }

        if (!artifactIds.length) {
            return;
        }

        const fieldsToRead = this._getArtifactFields();

        let artifacts;
        try {
            artifacts = await this.orm.read("mail.call.artifact", artifactIds, fieldsToRead);
        } catch (e) {
            if (this.activeResId !== initialResId) {
                return;
            }
            this.state.error = _t("Could not load call recordings");
            console.error(e);
            return;
        }

        if (this.activeResId !== initialResId) {
            console.log("[CallDebrief _loadData] Aborted due to activeResId !== initialResId!");
            return;
        }

        if (!artifacts.length) {
            return;
        }

        const mediaIds = artifacts.flatMap((a) => a.media_id?.[0] ?? []);
        const attachmentData = await this.orm.read("ir.attachment", mediaIds, ["mimetype"]);

        if (this.activeResId !== initialResId) {
            return;
        }

        const mimeMap = Object.fromEntries(attachmentData.map((a) => [a.id, a.mimetype]));

        const segments = [];
        for (const art of artifacts) {
            const startSec = art.start_ms / 1000;
            if (art.media_id) {
                const mediaId = art.media_id[0];
                const mime = mimeMap[mediaId] || "";
                const isVideo = mime.startsWith("video/");
                const isAudio = mime.startsWith("audio/");

                if (isVideo || isAudio) {
                    const endSec = art.end_ms / 1000;
                    segments.push({
                        id: art.id,
                        mediaId: mediaId,
                        mediaUrl: `/web/content/${mediaId}`,
                        type: isVideo ? "video" : "audio",
                        startSec: startSec,
                        endSec: endSec,
                        duration: endSec - startSec,
                    });
                }
            }
        }
        segments.sort((a, b) => a.startSec - b.startSec);

        this.state.mediaSegments = segments;
        if (segments.length > 0) {
            this.state.currentSegment = segments[0];
        }

        return artifacts;
    }

    /**
     * Hook to provide fields to read from mail.call.artifact.
     * Overridden in AI module to add AI-specific fields.
     */
    _getArtifactFields() {
        return ["media_id", "start_ms", "end_ms"];
    }

    /**
     * Finds the appropriate media segment for the given timestamp or artifact ID.
     */
    _findTargetSegment(timestamp, artifactId) {
        if (artifactId) {
            return this.state.mediaSegments.find((s) => s.id === artifactId);
        }

        let nextSegment;
        for (const segment of this.state.mediaSegments) {
            if (timestamp >= segment.startSec && timestamp < segment.endSec) {
                return segment; // Exact match found
            }
            // Track the closest upcoming segment if we fall in a gap
            if (segment.startSec > timestamp) {
                if (!nextSegment || segment.startSec < nextSegment.startSec) {
                    nextSegment = segment;
                }
            }
        }
        return nextSegment;
    }

    /**
     * Applies the target segment, timeline position, and play state to the <video>/<audio> element.
     */
    _alignMediaElement(targetSegment, relativeTime, autoplay, originalOptions) {
        if (this.state.currentSegment !== targetSegment) {
            this.isSwitchingSegment = true;
            this.state.currentSegment = targetSegment;
            this.onMediaLoadedCallback = () => {
                this.isSwitchingSegment = false;
                const mediaPlayer = this.mediaPlayer();
                if (mediaPlayer) {
                    mediaPlayer.currentTime = relativeTime;
                    if (autoplay) {
                        mediaPlayer.play().catch(() => {});
                    }
                }
            };
        } else {
            const mediaPlayer = this.mediaPlayer();
            if (mediaPlayer) {
                mediaPlayer.currentTime = relativeTime;
                if (autoplay) {
                    mediaPlayer.play().catch(() => {});
                }
            } else {
                // We must defer seeking if the media element hasn't been rendered or loaded yet.
                this.onMediaLoadedCallback = () => this.setPlaybackTime(originalOptions);
            }
        }
    }

    /** Given a point in time decides which audio/video segment should we be playing,
     * and exactly where inside that file should I be?
     */
    setPlaybackTime(options = {}) {
        const {
            timestamp = this.state.currentTime,
            play: autoplay = this.state.isPlaying,
            artifactId,
        } = options;

        this.state.currentTime = timestamp;

        if (!this.state.mediaSegments.length) {
            return;
        }

        const targetSegment = this._findTargetSegment(timestamp, artifactId);

        if (!targetSegment) {
            // Reached the end of all available media
            if (this.state.currentSegment) {
                this._pause(false);
            }
            return;
        }

        // If we fell into a break between recordings
        // todo Maybe implement a virtual clock, it'd continue playing during silence
        if (!artifactId && targetSegment.startSec > timestamp) {
            const gap = targetSegment.startSec - timestamp;
            if (gap < 2.0) {
                // Snap to the start of the next segment for small technical gaps
                this.state.currentTime = targetSegment.startSec;
            } else {
                // For larger gaps, pause and remain at the current time without snapping
                this._pause(false);
                this.state.currentSegment = undefined;
                return;
            }
        }

        const relativeTime = Math.max(0, this.state.currentTime - targetSegment.startSec);
        this._alignMediaElement(targetSegment, relativeTime, autoplay, options);
    }

    /**
     * Pauses the media element and optionally displays a feedback message.
     * @param {string|boolean} feedback - Optional text to display alongside the pause icon. Pass false to suppress feedback.
     */
    _pause(feedback = true) {
        const mediaPlayer = this.mediaPlayer();
        if (mediaPlayer) {
            mediaPlayer.pause();
        }
        this.state.isPlaying = false;
        if (feedback !== false) {
            this.showVideoFeedback(typeof feedback === "string" ? feedback : undefined, "fa-pause");
        }
    }

    onTimeUpdate(ev) {
        if (!this.state.currentSegment || ev.target.seeking || this.isSwitchingSegment) {
            return;
        }
        if (this.skipNextTimeUpdate) {
            this.skipNextTimeUpdate = false;
            return;
        }

        const mediaTime = ev.target.currentTime;
        // Pre-emptively switch to next segment to ensure gapless playback
        if (mediaTime >= this.state.currentSegment.duration - 0.2) {
            this.onMediaEnded();
            return;
        }

        const globalTime = this.state.currentSegment.startSec + mediaTime;
        this.state.currentTime = globalTime;
    }

    /**
     * Handles the end of the current media segment.
     * Transitions to the next segment if possible otherwise pauses. 
     */
    onMediaEnded() {
        if (this.isSwitchingSegment) {
            return;
        }
        this.isSwitchingSegment = true;

        const currentIndex = this.state.mediaSegments.indexOf(this.state.currentSegment);
        if (currentIndex < this.state.mediaSegments.length - 1) {
            const nextSegment = this.state.mediaSegments[currentIndex + 1];
            const gap = nextSegment.startSec - this.state.currentSegment.endSec;
            if (gap < 2.0) {
                this.setPlaybackTime({
                    timestamp: nextSegment.startSec,
                    play: true,
                    artifactId: nextSegment.id,
                });
            } else {
                // Large gap: pause at the end of the current segment
                this.setPlaybackTime({
                    timestamp: this.state.currentSegment.endSec,
                    play: false,
                });
                this.isSwitchingSegment = false;
            }
        } else {
            this._pause(false);
            this.isSwitchingSegment = false;
        }
    }

    _onMediaLoaded() {
        if (this.onMediaLoadedCallback) {
            this.onMediaLoadedCallback();
            this.onMediaLoadedCallback = null;
        }
    }

    adjustPlaybackRate(delta) {
        const currentRate = this.state.playbackRate;
        let closestIndex = -1;
        let minDiff = Infinity;
        for (let i = 0; i < this.playbackRates.length; i++) {
            const diff = Math.abs(this.playbackRates[i] - currentRate);
            if (diff < minDiff) {
                minDiff = diff;
                closestIndex = i;
            }
        }
        if (closestIndex === -1) {
            return;
        }

        let newIndex = closestIndex + delta;
        newIndex = Math.max(0, Math.min(newIndex, this.playbackRates.length - 1));

        const newRate = this.playbackRates[newIndex];
        this.state.playbackRate = newRate;
        this.showVideoFeedback(`${newRate}x`);
    }

    showVideoFeedback(text, icon) {
        this.state.feedback = { text, icon, id: Date.now() };
        if (this.feedbackTimeout) {
            clearTimeout(this.feedbackTimeout);
        }
        this.feedbackTimeout = setTimeout(() => {
            this.state.feedback = null;
        }, 750);
    }

    showMediaControlsFeedback(action) {
        const el = this.rootElement()?.querySelector(`[data-control-feedback="${action}"]`);
        if (!el) {
            return;
        }
        el.classList.remove("o-CallDebrief-hotkeyFeedback");
        void el.offsetWidth; // Force reflow to restart animation
        el.classList.add("o-CallDebrief-hotkeyFeedback");
        el.addEventListener("animationend", () => el.classList.remove("o-CallDebrief-hotkeyFeedback"), { once: true });
    }

    togglePlay() {
        const media = this.mediaPlayer();
        if (!media) {
            return;
        }
        if (this.state.currentTime >= this.callDurationSeconds - 0.5) {
            this.showVideoFeedback(_t("End of Media"));
            return;
        }
        if (this.state.isPlaying) {
            this._pause();
        } else {
            media.play().catch((e) => {
                this.state.isPlaying = false;
                this.showVideoFeedback(_t("Playback Error"));
            });
            this.state.isPlaying = true;
            this.showVideoFeedback(undefined, "fa-play");
        }
    }

    seekRelative(delta) {
        const newTime = Math.max(
            0,
            Math.min(this.callDurationSeconds, this.state.currentTime + delta)
        );
        this.setPlaybackTime({ timestamp: newTime });
        const direction = delta > 0 ? "fa-forward" : "fa-backward";
        this.showVideoFeedback(undefined, direction);
    }

    setPlaybackRate(ev) {
        this.state.playbackRate = parseFloat(ev.target.value);
    }

    adjustVolume(delta) {
        const newVolume = Math.max(0, Math.min(1, this.state.volume + delta));
        this.state.volume = newVolume;
        this.state.isMuted = this.state.volume === 0;
    }

    setVolume(ev) {
        this.state.volume = parseFloat(ev.target.value);
        this.state.isMuted = this.state.volume === 0;
    }

    onVolumeChange(ev) {
        this.state.volume = ev.target.volume;
        this.state.isMuted = ev.target.muted;
    }

    onRateChange(ev) {
        this.state.playbackRate = ev.target.playbackRate;
    }

    toggleMute() {
        this.state.isMuted = !this.state.isMuted;
        if (!this.state.isMuted && this.state.volume === 0) {
            this.state.volume = 0.5;
        }
        this.showVideoFeedback(undefined, this.state.isMuted ? "fa-volume-off" : "fa-volume-up");
    }

    toggleFullscreen() {
        const rootEl = this.rootElement();
        if (!rootEl || !this.hasVideo) {
            return;
        }
        if (!document.fullscreenElement) {
            rootEl.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }
}

export const callDebriefField = {
    component: CallDebrief,
    displayName: _t("Call Debrief"),
    supportedOptions: [
        {
            label: _t("Start Date Field"),
            name: "callStartDateField",
            type: "string",
        },
        {
            label: _t("End Date Field"),
            name: "callEndDateField",
            type: "string",
        },
    ],
    supportedTypes: ["one2many", "many2many"],
    extractProps: ({ options }) => ({
        callStartDateField: options.callStartDateField,
        callEndDateField: options.callEndDateField,
    }),
};

registry.category("fields").add("call_debrief", callDebriefField);
