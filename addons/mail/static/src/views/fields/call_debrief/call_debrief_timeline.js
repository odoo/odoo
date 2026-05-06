import { Component, onWillUnmount, props, signal, proxy } from "@odoo/owl";
import { formatDuration } from "@mail/views/fields/call_debrief/call_debrief_utils";

export class CallDebriefTimeline extends Component {
    static template = "mail.CallDebriefTimeline";
    static props = {
        // Total length of the call in seconds.
        totalDuration: { type: Number },
        // Array of media segment objects { id, startSec, endSec, duration, ... }
        mediaSegments: { type: Array, optional: true },
        media: { type: Object, optional: true },
        // Callback function called when the user clicks/drags to seek: ({ timestamp }) => void
        onSeek: { type: Function },
        // The current playback position in global call seconds.
        currentTime: { type: Number, optional: true },
    };

    props = props();

    setup() {
        this.timeline = signal(null);
        this.timestamp = signal(null);
        this.isDragging = false;
        this.state = proxy({
            hoverTimestamp: 0,
            hasHoverPosition: false,
        });

        this.onDragMove = this.onDragMove.bind(this);
        this.onDragEnd = this.onDragEnd.bind(this);

        onWillUnmount(() => {
            window.removeEventListener("pointermove", this.onDragMove);
            window.removeEventListener("pointerup", this.onDragEnd);
            window.removeEventListener("pointercancel", this.onDragEnd);
        });
    }

    formatDuration(seconds) {
        return formatDuration(seconds, this.props.totalDuration);
    }

    _stylePositionPlayhead() {
        if (!this.props.totalDuration) {
            return "left: 0%;";
        }
        const percentage = Math.min(100, (this.props.currentTime / this.props.totalDuration) * 100);
        return `left: ${percentage}%;`;
    }

    _stylePositionTimestamp() {
        if (!this.props.totalDuration) {
            return "left: 0%;";
        }
        const el = this.timestamp();
        const timestampWidth = el ? el.getBoundingClientRect().width : 0;
        const minOffset = timestampWidth / 2;

        const currentTimestamp = this.displayedTimestamp;
        const percentage = Math.min(100, (currentTimestamp / this.props.totalDuration) * 100);
        return `left: clamp(${minOffset}px, ${percentage}%, calc(100% - ${minOffset}px));`;
    }

    _stylePositionMediaSegment(media) {
        if (!this.props.totalDuration || !media || !media.duration) {
            return `left: 0%; width: 0%;`;
        }
        const start = media.startSec || 0;
        const width = Math.min(100, (media.duration / this.props.totalDuration) * 100);
        const left = (start / this.props.totalDuration) * 100;
        return `left: ${left}%; width: ${width}%;`;
    }

    _stylePositionMediaProgress(media) {
        if (!this.props.totalDuration || !media || !media.duration) {
            return `width: 0%;`;
        }
        const currentTime = this.props.currentTime || 0;
        const playedDuration = Math.max(0, Math.min(currentTime - media.startSec, media.duration));
        const width = (playedDuration / media.duration) * 100;
        return `width: ${width}%;`;
    }

    onDragStart(ev) {
        // For mouse, only react to left click.
        if (ev.pointerType === "mouse" && ev.button !== 0) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault(); // Prevents defualt text selection
        this.isDragging = true;
        window.addEventListener("pointermove", this.onDragMove);
        window.addEventListener("pointerup", this.onDragEnd);
        window.addEventListener("pointercancel", this.onDragEnd);
        this._updateSeek(ev);
    }

    onDragMove(ev) {
        if (this.isDragging) {
            ev.stopPropagation();
            // Mouse released outside the timeline.
            if (ev.pointerType === "mouse" && ev.buttons === 0) {
                this.onDragEnd();
                return;
            }
            this._updateSeek(ev);
        }
    }

    onDragEnd(ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.isDragging = false;
        window.removeEventListener("pointermove", this.onDragMove);
        window.removeEventListener("pointerup", this.onDragEnd);
        window.removeEventListener("pointercancel", this.onDragEnd);
    }

    _getTimestampFromClientX(clientX) {
        const el = this.timeline();
        if (!el || !this.props.totalDuration) {
            return 0;
        }
        const rect = el.getBoundingClientRect();
        const edgeOffset = 8; // Half of the playhead size
        const extendedLeft = rect.left - edgeOffset;
        const extendedWidth = rect.width + edgeOffset * 2;
        const progress = Math.max(0, Math.min(1, (clientX - extendedLeft) / extendedWidth));
        return progress * this.props.totalDuration;
    }

    _updateSeek(ev) {
        const newTimestamp = this._getTimestampFromClientX(ev.clientX);
        this.state.hoverTimestamp = newTimestamp;
        this.state.hasHoverPosition = true;
        this.props.onSeek({ timestamp: newTimestamp });
    }

    onHoverMove(ev) {
        this.state.hoverTimestamp = this._getTimestampFromClientX(ev.clientX);
        this.state.hasHoverPosition = true;
    }

    onLeaveMove(ev) {
        setTimeout(() => this.state.hasHoverPosition = false, 200);
    }

    get displayedTimestamp() {
        if (this.state.hasHoverPosition) {
            return this.state.hoverTimestamp;
        }
        return this.props.currentTime;
    }

    get formattedTotalDuration() {
        return this.formatDuration(this.props.totalDuration);
    }
}
