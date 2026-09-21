/** @odoo-module native */
import { registry } from "@web/core/registry";

import {
    MEDIA_TIMELINE_FIELDS,
    MediaTimelineField,
} from "@media/media_timeline/media_timeline_field";

/**
 * @typedef {Object} Cue
 * @property {number} start
 * @property {number} end
 * @property {string} text
 * @property {string} speaker
 */

export class TranscriptTimelineField extends MediaTimelineField {
    static template = "speech.TranscriptTimelineField";

    /** @param {any} record */
    _toSegment(record) {
        return { ...super._toSegment(record), cues: record.data.transcript_cues ?? [] };
    }

    /** @returns {Cue[]} */
    get cues() {
        return this.current?.cues ?? [];
    }

    /**
     * @param {Cue} cue
     * @returns {boolean}
     */
    isCueActive(cue) {
        const offset = (this.state.positionMs - (this.current?.startMs ?? 0)) / 1000;
        return offset >= cue.start && offset < cue.end;
    }

    /** @param {Cue} cue */
    onCueClick(cue) {
        this.seek((this.current?.startMs ?? 0) + Math.round(cue.start * 1000));
    }
}

registry.category("fields").add("transcript_timeline", {
    component: TranscriptTimelineField,
    supportedTypes: ["one2many"],
    relatedFields: () => [
        ...MEDIA_TIMELINE_FIELDS,
        { name: "transcript_cues", type: "json" },
    ],
});
