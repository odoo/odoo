import { Component, onWillUnmount, props, signal } from "@odoo/owl";
import { formatFloatTime } from "@web/views/fields/formatters";

export class CallDebriefTimeline extends Component {
    static template = "mail.CallDebriefTimeline";
    static props = {
        // Total length of the call in seconds.
        totalDuration: { type: Number },
        // Array of media segment objects { id, startSec, endSec, duration, ... }
        mediaSegments: { type: Array, optional: true },
        // Callback function called when the user clicks/drags to seek: ({ timestamp }) => void
        onSeek: { type: Function },
        // The current playback position in global call seconds.
        currentTime: { type: Number, optional: true },
    };

    props = props();

    setup() {
        this.timeline = signal(null);
        this.isDragging = false;

        this.onDragMove = this.onDragMove.bind(this);
        this.onDragEnd = this.onDragEnd.bind(this);

        onWillUnmount(() => {
            window.removeEventListener("mousemove", this.onDragMove);
            window.removeEventListener("mouseup", this.onDragEnd);
        });
    }

    formatDuration(seconds) {
        const formatted = formatFloatTime(seconds || 0, {
            unit: "seconds",
            showSeconds: true,
            numeric: true,
        });
        if (this.props.totalDuration < 3600) {
            return formatted.slice(2);
        }
        return formatted;
    }

    _stylePositionPlayhead() {
        if (!this.props.totalDuration) {
            return "left: 0%;";
        }
        const percentage = Math.min(100, (this.props.currentTime / this.props.totalDuration) * 100);
        return `left: ${percentage}%;`;
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

    onDragStart(ev) {
        // Only on left click
        if (ev.button !== 0) {
            return;
        }
        ev.stopPropagation();
        ev.preventDefault(); // Prevents defualt text selection
        this.isDragging = true;
        window.addEventListener("mousemove", this.onDragMove);
        window.addEventListener("mouseup", this.onDragEnd);
        this._updateSeek(ev);
    }

    onDragMove(ev) {
        if (this.isDragging) {
            ev.stopPropagation();
            // Mouse realased outside the window
            if (ev.buttons === 0) {
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
        window.removeEventListener("mousemove", this.onDragMove);
        window.removeEventListener("mouseup", this.onDragEnd);
    }

    _getTimestampFromClientX(clientX) {
        const el = this.timeline();
        if (!el || !this.props.totalDuration) {
            return 0;
        }
        const rect = el.getBoundingClientRect();
        const progress = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));
        return progress * this.props.totalDuration;
    }

    _updateSeek(ev) {
        const newTimestamp = this._getTimestampFromClientX(ev.clientX);
        this.props.onSeek({ timestamp: newTimestamp });
    }

    get formattedTotalDuration() {
        return this.formatDuration(this.props.totalDuration);
    }
}
