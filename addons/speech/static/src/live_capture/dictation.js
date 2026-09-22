// @ts-check
/** @odoo-module native */
import { ChunkRecorder } from "@speech/live_capture/chunk_recorder";

export const SETTLE_TIMEOUT_MS = 60000;

/**
 * @typedef {{
 *   orm: any,
 *   bus: any,
 *   onChunkSent: (index: number) => void,
 *   onChunkText: (index: number, text: string) => void,
 *   onError?: (error: any) => void,
 * }} DictationCallbacks
 */

export class Dictation {
    /** @param {DictationCallbacks} callbacks */
    constructor({ orm, bus, onChunkSent, onChunkText, onError }) {
        this.orm = orm;
        this.bus = bus;
        this.onChunkSent = onChunkSent;
        this.onChunkText = onChunkText;
        this.onError = onError || (() => {});
        /** @type {number | null} */
        this.id = null;
        /** @type {string | null} */
        this.channel = null;
        this.sequence = 0;
        /** @type {Map<number, number>} */
        this.pending = new Map();
        /** @type {Map<number, string>} */
        this.early = new Map();
        /** @type {Set<Promise<void>>} */
        this.sending = new Set();
        /** @type {(() => void) | null} */
        this.settled = null;
        this.recorder = new ChunkRecorder((chunk) => this.send(chunk));
        this.onNotification = this.onNotification.bind(this);
    }

    get recording() {
        return this.id !== null;
    }

    /**
     * @param {{resModel?: string, resId?: number, language?: string, prompt?: string}} target
     */
    async start({ resModel, resId, language, prompt }) {
        const { id, channel } = await this.orm.call(
            "speech.dictation",
            "start_dictation",
            [],
            { res_model: resModel, res_id: resId, language, prompt },
        );
        this.id = id;
        this.channel = channel;
        this.bus.addChannel(channel);
        this.bus.subscribe("speech.live", this.onNotification);
        try {
            await this.recorder.start();
        } catch (error) {
            await this.close();
            throw error;
        }
    }

    /** @param {import("@speech/live_capture/chunk_recorder").Chunk} chunk */
    send(chunk) {
        const index = this.sequence++;
        this.onChunkSent(index);
        const sending = this.orm
            .call("speech.dictation", "push_chunk", [this.id], {
                audio: chunk.audio,
                start_s: chunk.startS,
                duration_s: chunk.durationS,
                mimetype: chunk.mimetype,
            })
            .then((/** @type {number} */ segmentId) => {
                this.pending.set(segmentId, index);
                if (this.early.has(segmentId)) {
                    this.resolve(segmentId, this.early.get(segmentId) || "");
                    this.early.delete(segmentId);
                }
            })
            .catch((/** @type {any} */ error) => {
                this.onChunkText(index, "");
                this.onError(error);
            })
            .finally(() => {
                this.sending.delete(sending);
                this.checkSettled();
            });
        this.sending.add(sending);
    }

    /** @param {{model: string, id: number, event: string, segment_id?: number, text?: string}} payload */
    onNotification(payload) {
        if (
            !payload ||
            payload.model !== "speech.dictation" ||
            payload.id !== this.id ||
            payload.event !== "chunk" ||
            !payload.segment_id
        ) {
            return;
        }
        this.resolve(payload.segment_id, payload.text || "");
    }

    /**
     * @param {number} segmentId
     * @param {string} text
     */
    resolve(segmentId, text) {
        const index = this.pending.get(segmentId);
        if (index === undefined) {
            this.early.set(segmentId, text);
            return;
        }
        this.pending.delete(segmentId);
        this.onChunkText(index, text);
        this.checkSettled();
    }

    checkSettled() {
        if (this.settled && !this.pending.size && !this.sending.size) {
            this.settled();
        }
    }

    async stop() {
        if (!this.recording) {
            return;
        }
        await this.recorder.stop();
        await Promise.all([...this.sending]);
        await this.orm.call("speech.dictation", "action_stop_live", [this.id]);
        await new Promise((resolve) => {
            this.settled = () => resolve(undefined);
            setTimeout(() => resolve(undefined), SETTLE_TIMEOUT_MS);
            this.checkSettled();
        });
        for (const index of this.pending.values()) {
            this.onChunkText(index, "");
        }
        await this.close();
    }

    async close() {
        if (this.channel) {
            this.bus.unsubscribe("speech.live", this.onNotification);
            this.bus.deleteChannel(this.channel);
        }
        this.pending.clear();
        this.early.clear();
        this.settled = null;
        this.channel = null;
        this.id = null;
    }
}
