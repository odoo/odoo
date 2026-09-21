/** @odoo-module native */
import { Component, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { standardFieldProps } from "@web/fields/standard_field_props";

const RATES = [0.5, 0.75, 1, 1.25, 1.5, 2];

/**
 * @typedef {Object} Segment
 * @property {number} id
 * @property {number} attachmentId
 * @property {number} startMs
 * @property {number} endMs
 * @property {string} mimetype
 * @property {boolean} released
 */

export class MediaTimelineField extends Component {
    static template = "media.MediaTimelineField";
    static props = { ...standardFieldProps };

    setup() {
        this.player = useRef("player");
        this.state = useState({
            index: 0,
            playing: false,
            positionMs: 0,
            rate: 1,
        });
        onWillUnmount(() => this.player.el?.pause());
    }

    /** @returns {Segment[]} */
    get segments() {
        const records = this.props.record.data[this.props.name]?.records ?? [];
        return records
            .map((record) => this._toSegment(record))
            .sort((a, b) => a.startMs - b.startMs);
    }

    /**
     * @param {any} record
     * @returns {Segment}
     */
    _toSegment(record) {
        return {
            id: record.resId,
            attachmentId: record.data.attachment_id?.[0] ?? record.data.attachment_id,
            startMs: record.data.start_ms ?? 0,
            endMs: record.data.end_ms ?? 0,
            mimetype: record.data.mimetype ?? "",
            released: Boolean(record.data.content_released_at),
        };
    }

    /** @returns {number} */
    get durationMs() {
        const segments = this.segments;
        return segments.length ? segments.at(-1).endMs : 0;
    }

    /** @returns {Segment|undefined} */
    get current() {
        return this.segments[this.state.index];
    }

    /** @returns {boolean} */
    get isVideo() {
        return (this.current?.mimetype ?? "").startsWith("video/");
    }

    /** @returns {string} */
    get source() {
        const segment = this.current;
        return segment && !segment.released
            ? `/web/content/${segment.attachmentId}`
            : "";
    }

    /** @returns {boolean} */
    get isReleased() {
        return Boolean(this.current?.released);
    }

    /**
     * @param {number} ms
     * @returns {string}
     */
    format(ms) {
        const total = Math.max(Math.round(ms / 1000), 0);
        const minutes = String(Math.floor(total / 60)).padStart(2, "0");
        const seconds = String(total % 60).padStart(2, "0");
        return `${minutes}:${seconds}`;
    }

    /**
     * @param {Segment} segment
     * @returns {string}
     */
    barStyle(segment) {
        const span = this.durationMs || 1;
        const left = (segment.startMs / span) * 100;
        const width = ((segment.endMs - segment.startMs) / span) * 100;
        return `left:${left}%;width:${width}%`;
    }

    /** @returns {string} */
    get headStyle() {
        const span = this.durationMs || 1;
        return `left:${(this.state.positionMs / span) * 100}%`;
    }

    /** @param {number} ms */
    async seek(ms) {
        const segments = this.segments;
        const index = segments.findIndex(
            (segment) => ms >= segment.startMs && ms < segment.endMs,
        );
        const target = index === -1 ? segments.length - 1 : index;
        if (target < 0) {
            return;
        }
        const changed = target !== this.state.index;
        this.state.index = target;
        this.state.positionMs = ms;
        if (changed) {
            await this._reload();
        }
        if (this.player.el) {
            this.player.el.currentTime = Math.max(
                (ms - segments[target].startMs) / 1000,
                0,
            );
        }
    }

    /** @param {PointerEvent} ev */
    onBarClick(ev) {
        const bounds = ev.currentTarget.getBoundingClientRect();
        const share = (ev.clientX - bounds.left) / bounds.width;
        this.seek(Math.round(share * this.durationMs));
    }

    async togglePlay() {
        const player = this.player.el;
        if (!player) {
            return;
        }
        if (player.paused) {
            await player.play();
            this.state.playing = true;
        } else {
            player.pause();
            this.state.playing = false;
        }
    }

    cycleRate() {
        const next = (RATES.indexOf(this.state.rate) + 1) % RATES.length;
        this.state.rate = RATES[next];
        if (this.player.el) {
            this.player.el.playbackRate = this.state.rate;
        }
    }

    onTimeUpdate() {
        const player = this.player.el;
        if (!player || !this.current) {
            return;
        }
        this.state.positionMs = this.current.startMs + player.currentTime * 1000;
    }

    async onEnded() {
        const next = this.state.index + 1;
        if (next >= this.segments.length) {
            this.state.playing = false;
            return;
        }
        this.state.index = next;
        this.state.positionMs = this.segments[next].startMs;
        await this._reload();
        await this.player.el?.play();
    }

    async _reload() {
        const player = this.player.el;
        if (!player) {
            return;
        }
        player.load();
        player.playbackRate = this.state.rate;
    }

    /** @returns {string} */
    get emptyMessage() {
        return _t("Nothing was recorded.");
    }

    /** @returns {string} */
    get releasedMessage() {
        return _t("The audio was removed at the end of its retention.");
    }
}

export const MEDIA_TIMELINE_FIELDS = [
    { name: "start_ms", type: "integer" },
    { name: "end_ms", type: "integer" },
    { name: "attachment_id", type: "many2one", relation: "ir.attachment" },
    { name: "mimetype", type: "char" },
    { name: "content_released_at", type: "datetime" },
];

registry.category("fields").add("media_timeline", {
    component: MediaTimelineField,
    supportedTypes: ["one2many"],
    relatedFields: () => MEDIA_TIMELINE_FIELDS,
});
