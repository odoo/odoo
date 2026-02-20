/** @odoo-module **/

import {
    Component,
    useState,
    onWillStart,
    useRef,
    onWillUpdateProps,
    onMounted,
    onWillUnmount,
    useEffect,
} from "@odoo/owl";
import { formatDuration } from "./call_debrief_utils";
import { CallDebriefTimeline } from "./call_debrief_timeline";
import { CallDebriefMediaControls } from "./call_debrief_media_controls";
import { parseTimedText } from "./transcript_parser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { deserializeDateTime } from "@web/core/l10n/dates";

export class CallDebrief extends Component {
    static template = "mail.CallDebrief";
    static props = {
        ...standardFieldProps,
        callStartDateField: { type: String },
        callEndDateField: { type: String },
    };

    static components = { CallDebriefTimeline, CallDebriefMediaControls };

    setup() {
        this.callDurationSeconds = 0;
        this.playbackRates = [0.25, 0.5, 0.75, 0.9, 1, 1.25, 1.5, 1.75, 2, 3];
        this.skipNextTimeUpdate = false;
        this.isSwitchingSegment = false;

        this.mediaPlayerRef = useRef("mediaPlayer");
        this.transcriptContainerRef = useRef("transcriptContainer");
        this.highlightedLineRef = null;

        this.orm = useService("orm");
        this.state = useState({
            currentTime: 0,
            mediaSegments: [],
            currentSegment: undefined,
            transcriptLines: [],
            plainTextTranscript: null,
            error: "",
            isPlaying: false,
            playbackRate: 1,
            volume: 1,
            isMuted: false,
            feedback: { text: "", id: Date.now() },
        });

        this.onMediaLoadedCallback = null;
        this.formatDuration = formatDuration;

        onWillStart(() => this._loadData(this.props));

        onWillUpdateProps(async (nextProps) => {
            const hasIdChanged = this.props.record.resId !== nextProps.record.resId;
            const hasFieldChanged =
                this.props.record.data[this.props.name] !== nextProps.record.data[nextProps.name];
            if (hasIdChanged || hasFieldChanged) {
                await this._loadData(nextProps);
            }
        });

        onMounted(() => {
            window.addEventListener("keydown", this.onKeyDown);
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this.onKeyDown);
            if (this.feedbackTimeout) {
                clearTimeout(this.feedbackTimeout);
            }
        });

        useEffect(
            () => {
                const media = this.mediaPlayerRef.el;
                if (media) {
                    media.playbackRate = this.state.playbackRate;
                    media.volume = this.state.volume;
                    media.muted = this.state.isMuted;
                }
            },
            () => [
                this.state.playbackRate,
                this.state.volume,
                this.state.isMuted,
                this.state.currentSegment,
            ]
        );
    }

    get hasMedia() {
        return this.state.mediaSegments.length > 0;
    }

    get hasVideo() {
        return this.state.currentSegment?.type === "video";
    }

    get hasTranscriptLines() {
        return this.state.transcriptLines.length > 0;
    }

    get hasPlainTextTranscript() {
        return !!this.state.plainTextTranscript;
    }

    get hasTranscript() {
        return this.hasTranscriptLines || this.hasPlainTextTranscript;
    }

    onMediaError = () => {
        this.showFeedback("Media Error");
        console.warn("Media playback error. The format might not be supported by your browser.");
    };

    _initCallTiming(start, end) {
        if (!start || !end) {
            this.state.error =
                "CallDebrief widget needs start and end datetime from the parent record.";
            this._resetState();
            return false;
        }
        const callStartDate = typeof start === "string" ? deserializeDateTime(start) : start;
        const callEndDate = typeof end === "string" ? deserializeDateTime(end) : end;

        const duration = callEndDate.diff(callStartDate, "seconds").seconds;
        if (duration < 0) {
            this.state.error = "Invalid call timing: end date is before start date.";
            this._resetState();
            return false;
        }
        this.callDurationSeconds = duration;
        return true;
    }

    _resetState() {
        this.state.mediaSegments = [];
        this.state.currentSegment = undefined;
        this.state.transcriptLines = [];
        this.state.plainTextTranscript = null;
        this.state.currentTime = 0;
    }

    async _loadData(props) {
        this.state.error = "";
        this.state.isPlaying = false;
        this.state.currentSegment = undefined;
        this.state.mediaSegments = [];
        this.state.transcriptLines = [];

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

        const optionalFields = await this.orm.call("call.artifact", "fields_get", [
            ["is_stt", "transcript"],
        ]);
        const fieldsToRead = ["media_id", "start_ms", "end_ms", ...Object.keys(optionalFields)];

        let artifacts;
        try {
            artifacts = await this.orm.read("call.artifact", artifactIds, fieldsToRead);
        } catch (e) {
            this.state.error = "Could not load call artifacts.";
            console.error(e);
            return;
        }

        if (!artifacts || !artifacts.length) {
            return;
        }

        const mediaIds = artifacts.map((a) => a.media_id?.[0]).filter(Boolean);
        const attachmentData = await this.orm.read("ir.attachment", mediaIds, ["mimetype"]);
        const mimeMap = Object.fromEntries(attachmentData.map((a) => [a.id, a.mimetype]));

        const segments = [];
        const allTranscriptLines = [];

        for (const art of artifacts) {
            const startSec = art.start_ms / 1000;

            if (art.transcript) {
                allTranscriptLines.push(...this._buildTranscriptLines(art.transcript, startSec));
            }

            if (!art.is_stt && art.media_id) {
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
        allTranscriptLines.sort((a, b) => a.startSecRelToCall - b.startSecRelToCall);

        this.state.mediaSegments = segments;
        this.state.transcriptLines = allTranscriptLines;

        if (segments.length > 0) {
            this.state.currentSegment = segments[0];
        }
    }

    /**
     * Parses raw transcript text and offsets its timestamps to align with
     * the call's global timeline.
     *
     * @param {string} transcriptText Raw transcript content (e.g. VTT).
     * @param {number} offsetSec The start time of the artifact in seconds relative to the call.
     * @returns {Object[]} Array of transcript line objects with global timestamps.
     */
    _buildTranscriptLines(transcriptText, offsetSec) {
        const lines = [];
        const parsed = parseTimedText(transcriptText);
        for (const line of parsed) {
            const startSecRelToCall = offsetSec + line.startSec;
            const endSecRelToCall = offsetSec + line.endSec;
            lines.push({
                ...line,
                startSecRelToCall,
                endSecRelToCall,
                isGap: false,
            });
        }
        return lines;
    }

    setPlaybackTime = (options = {}) => {
        const {
            timestamp = this.state.currentTime,
            play: autoplay = this.state.isPlaying,
            artifactId,
        } = options;
        console.log(
            "[CallDebrief] setPlaybackTime",
            timestamp,
            "autoplay:",
            autoplay,
            "artifactId:",
            artifactId
        );

        this.state.currentTime = timestamp;
        this.updateTranscriptHighlight(timestamp);

        if (!this.state.mediaSegments.length) {
            return;
        }

        let targetSegment;
        if (artifactId) {
            targetSegment = this.state.mediaSegments.find((s) => s.id === artifactId);
        }

        if (!targetSegment) {
            // Fallback to time-based search
            targetSegment = this.state.mediaSegments.find(
                (s) => timestamp >= s.startSec && timestamp < s.endSec // strict check
            );
        }

        if (!targetSegment) {
            targetSegment = this.state.mediaSegments.find((s) => s.startSec > timestamp);
            if (targetSegment) {
                console.log(
                    "[CallDebrief] Gap detected, jumping to next segment:",
                    targetSegment.id,
                    "start:",
                    targetSegment.startSec
                );
                this.state.currentTime = targetSegment.startSec;
            } else {
                console.log("[CallDebrief] End of all segments.");
                if (this.state.currentSegment) {
                    if (this.mediaPlayerRef.el) {
                        this.mediaPlayerRef.el.pause();
                    }
                    this.state.isPlaying = false;
                }
                return;
            }
        }

        const relativeTime = Math.max(0, this.state.currentTime - targetSegment.startSec);

        if (this.state.currentSegment !== targetSegment) {
            console.log(
                "[CallDebrief] Switching segment from",
                this.state.currentSegment?.id,
                "to",
                targetSegment.id
            );
            this.isSwitchingSegment = true;
            this.state.currentSegment = targetSegment;
            this.onMediaLoadedCallback = () => {
                console.log("[CallDebrief] Media loaded callback. Resetting switch flag.");
                this.isSwitchingSegment = false; // Reset flag after switch
                if (this.mediaPlayerRef.el) {
                    this.mediaPlayerRef.el.currentTime = relativeTime;
                    if (autoplay) {
                        this.mediaPlayerRef.el.play().catch(() => {});
                    }
                }
            };
        } else {
            console.log("[CallDebrief] Same segment seek.");
            this.isSwitchingSegment = false; // Reset if seeking in same segment
            if (this.mediaPlayerRef.el) {
                this.mediaPlayerRef.el.currentTime = relativeTime;
                if (autoplay) {
                    this.mediaPlayerRef.el.play().catch(() => {});
                }
            } else {
                this.onMediaLoadedCallback = () => this.setPlaybackTime(options);
            }
        }
    };

    onTimeUpdate = (ev) => {
        if (!this.state.currentSegment || ev.target.seeking || this.isSwitchingSegment) {
            // console.log("[CallDebrief] Skipping onTimeUpdate. Switching:", this.isSwitchingSegment, "Seeking:", ev.target.seeking);
            return;
        }
        if (this.skipNextTimeUpdate) {
            this.skipNextTimeUpdate = false;
            return;
        }

        const mediaTime = ev.target.currentTime;
        // Check if we passed the end of the segment (tolerance 0.2s to capture end before browser stops)
        if (mediaTime >= this.state.currentSegment.duration - 0.2) {
            console.log(
                "[CallDebrief] End detected via timeUpdate. Time:",
                mediaTime,
                "Duration:",
                this.state.currentSegment.duration
            );
            this.onMediaEnded();
            return;
        }

        const globalTime = this.state.currentSegment.startSec + mediaTime;
        this.state.currentTime = globalTime;
        this.updateTranscriptHighlight(globalTime);
    };

    onMediaEnded = () => {
        console.log("[CallDebrief] onMediaEnded triggered. Switching?", this.isSwitchingSegment);
        if (this.isSwitchingSegment) {
            return;
        }
        this.isSwitchingSegment = true;

        const currentIndex = this.state.mediaSegments.indexOf(this.state.currentSegment);
        if (currentIndex < this.state.mediaSegments.length - 1) {
            const nextSegment = this.state.mediaSegments[currentIndex + 1];
            console.log("[CallDebrief] Auto-advancing to segment:", nextSegment.id);
            // Jump to start of next segment
            this.setPlaybackTime({
                timestamp: nextSegment.startSec,
                play: true,
                artifactId: nextSegment.id,
            });
        } else {
            console.log("[CallDebrief] Final segment ended.");
            this.state.isPlaying = false;
            this.isSwitchingSegment = false;
        }
    };

    _onMediaLoaded = () => {
        if (this.onMediaLoadedCallback) {
            this.onMediaLoadedCallback();
            this.onMediaLoadedCallback = null;
        }
    };

    onLoadedMetadata = (ev) => {
        const duration = ev.target.duration;
        if (this.state.currentSegment && !Number.isNaN(duration)) {
            // Update actual duration from metadata if needed,
            // though we rely on db end_ms usually.
            // this.state.currentSegment.duration = duration;
        }
    };

    updateTranscriptHighlight(timestamp) {
        if (this.state.transcriptLines && this.state.transcriptLines.length > 0) {
            let closestLine = null;
            for (const line of this.state.transcriptLines) {
                if (line.startSecRelToCall <= timestamp) {
                    closestLine = line;
                } else {
                    break;
                }
            }
            if (closestLine) {
                const lineElement = this.transcriptContainerRef.el.querySelector(
                    `[data-timestamp="${closestLine.startSecRelToCall}"]`
                );
                if (lineElement) {
                    if (this.highlightedLineRef && this.highlightedLineRef !== lineElement) {
                        this.highlightedLineRef.classList.remove(
                            "o-CallDebrief-transcript-highlight"
                        );
                    }
                    lineElement.classList.add("o-CallDebrief-transcript-highlight");
                    this.highlightedLineRef = lineElement;
                    lineElement.scrollIntoView({ behavior: "smooth", block: "center" });
                }
            }
        }
    }

    _getHighlightedLineIndex() {
        if (!this.highlightedLineRef) {
            return -1;
        }
        const highlightedTimestamp = parseFloat(this.highlightedLineRef.dataset.timestamp);
        return this.state.transcriptLines.findIndex(
            (line) => line.startSecRelToCall === highlightedTimestamp
        );
    }

    onTranscriptLineClick = (line) => {
        this.setPlaybackTime({ timestamp: line.startSecRelToCall });
    };

    onKeyDown = (ev) => {
        const target = ev.target;
        if (
            ev.defaultPrevented ||
            ev.ctrlKey ||
            ev.metaKey ||
            ev.altKey ||
            target.isContentEditable ||
            ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
        ) {
            return;
        }

        switch (ev.key) {
            case "k":
            case " ":
                ev.preventDefault();
                this.togglePlay();
                break;
            case "j":
                this.seekRelative(-5);
                break;
            case "l":
                this.seekRelative(5);
                break;
            case "ArrowLeft":
                ev.preventDefault();
                this.seekRelative(-5);
                break;
            case "ArrowRight":
                ev.preventDefault();
                this.seekRelative(5);
                break;
            case "ArrowUp":
                ev.preventDefault();
                this._jumpToTranscriptLine(-1);
                break;
            case "ArrowDown":
                ev.preventDefault();
                this._jumpToTranscriptLine(1);
                break;
            case "<":
                ev.preventDefault();
                this.adjustPlaybackRate(-1);
                break;
            case ">":
                ev.preventDefault();
                this.adjustPlaybackRate(1);
                break;
            case "m":
                this.toggleMute();
                break;
        }
    };

    _jumpToTranscriptLine(offset) {
        if (!this.hasTranscriptLines) {
            return;
        }

        const currentLineIndex = this._getHighlightedLineIndex();
        let targetIndex = -1;

        if (currentLineIndex === -1) {
            targetIndex = offset > 0 ? 0 : this.state.transcriptLines.length - 1;
        } else {
            targetIndex = currentLineIndex + offset;
            while (
                targetIndex >= 0 &&
                targetIndex < this.state.transcriptLines.length &&
                this.state.transcriptLines[targetIndex].isGap
            ) {
                targetIndex += offset;
            }
        }

        if (targetIndex >= 0 && targetIndex < this.state.transcriptLines.length) {
            const targetLine = this.state.transcriptLines[targetIndex];
            this.skipNextTimeUpdate = true;
            this.setPlaybackTime({ timestamp: targetLine.startSecRelToCall });
        }
        this.showFeedback(`${offset > 0 ? "next" : "previous"} line`);
    }

    adjustPlaybackRate = (delta) => {
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
        this.showFeedback(`${newRate}x`);
    };

    showFeedback(text) {
        this.state.feedback = { text, id: Date.now() };
        if (this.feedbackTimeout) {
            clearTimeout(this.feedbackTimeout);
        }
        this.feedbackTimeout = setTimeout(() => {
            this.state.feedback.text = "";
        }, 750);
    }

    togglePlay = () => {
        const media = this.mediaPlayerRef.el;
        if (!media) {
            return;
        }
        if (this.state.currentTime >= this.callDurationSeconds - 0.5) {
            this.showFeedback("End of Media");
            return;
        }
        if (this.state.isPlaying) {
            media.pause();
            this.state.isPlaying = false;
            this.showFeedback("Pause");
        } else {
            media.play().catch((e) => {
                console.warn("Playback failed:", e);
                this.state.isPlaying = false;
                this.showFeedback("Playback Error");
            });
            this.state.isPlaying = true;
            this.showFeedback("Play");
        }
    };

    seekRelative = (delta) => {
        const newTime = Math.max(
            0,
            Math.min(this.callDurationSeconds, this.state.currentTime + delta)
        );
        this.setPlaybackTime({ timestamp: newTime });
        const direction = delta > 0 ? "+" : "-";
        this.showFeedback(`${direction} ${Math.abs(delta)}s`);
    };

    setPlaybackRate = (ev) => {
        this.state.playbackRate = parseFloat(ev.target.value);
    };

    adjustVolume = (delta) => {
        const newVolume = Math.max(0, Math.min(1, this.state.volume + delta));
        this.state.volume = newVolume;
        this.state.isMuted = this.state.volume === 0;
    };

    setVolume = (ev) => {
        this.state.volume = parseFloat(ev.target.value);
        this.state.isMuted = this.state.volume === 0;
    };

    toggleMute = () => {
        this.state.isMuted = !this.state.isMuted;
        if (!this.state.isMuted && this.state.volume === 0) {
            this.state.volume = 0.5;
        }
        this.showFeedback(this.state.isMuted ? "Muted" : "Unmuted");
    };
}

export const callDebriefField = {
    component: CallDebrief,
    displayName: "Call Debrief",
    supportedOptions: [
        {
            label: "Start Date Field",
            name: "callStartDateField",
            type: "string",
        },
        {
            label: "End Date Field",
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
