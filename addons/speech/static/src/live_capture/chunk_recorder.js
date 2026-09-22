// @ts-check
/** @odoo-module native */
import { url } from "@web/core/utils/urls";

export const MIN_CHUNK_S = 5;
export const MAX_CHUNK_S = 10;
export const TARGET_RATE = 16000;
const PAUSE_S = 0.3;
const SILENCE_RMS = 0.01;

/** @param {Float32Array} samples */
export function rms(samples) {
    let sum = 0;
    for (const sample of samples) {
        sum += sample * sample;
    }
    return samples.length ? Math.sqrt(sum / samples.length) : 0;
}

/**
 * @param {Float32Array} samples
 * @param {number} fromRate
 * @param {number} toRate
 */
export function downsample(samples, fromRate, toRate) {
    if (fromRate <= toRate) {
        return samples;
    }
    const ratio = fromRate / toRate;
    const result = new Float32Array(Math.floor(samples.length / ratio));
    for (let index = 0; index < result.length; index++) {
        const start = Math.floor(index * ratio);
        const end = Math.min(Math.floor((index + 1) * ratio), samples.length);
        let sum = 0;
        for (let cursor = start; cursor < end; cursor++) {
            sum += samples[cursor];
        }
        result[index] = sum / Math.max(end - start, 1);
    }
    return result;
}

/**
 * @param {Float32Array} samples
 * @param {number} sampleRate
 */
export function encodeWav(samples, sampleRate) {
    const bytes = new Uint8Array(44 + samples.length * 2);
    const view = new DataView(bytes.buffer);
    const ascii = (/** @type {number} */ offset, /** @type {string} */ text) => {
        for (let index = 0; index < text.length; index++) {
            view.setUint8(offset + index, text.charCodeAt(index));
        }
    };
    ascii(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    ascii(8, "WAVE");
    ascii(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    ascii(36, "data");
    view.setUint32(40, samples.length * 2, true);
    samples.forEach((sample, index) => {
        const clipped = Math.max(-1, Math.min(1, sample));
        view.setInt16(
            44 + index * 2,
            clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff,
            true,
        );
    });
    return bytes;
}

/** @param {Uint8Array} bytes */
export function toBase64(bytes) {
    let binary = "";
    for (let offset = 0; offset < bytes.length; offset += 0x8000) {
        binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
    }
    return btoa(binary);
}

/**
 * @typedef {{audio: string, startS: number, durationS: number, mimetype: string}} Chunk
 */

export class ChunkRecorder {
    /** @param {(chunk: Chunk) => void} onChunk */
    constructor(onChunk) {
        this.onChunk = onChunk;
        /** @type {Float32Array[]} */
        this.frames = [];
        this.length = 0;
        this.quiet = 0;
        this.offset = 0;
        this.sampleRate = TARGET_RATE;
        /** @type {MediaStream | null} */
        this.stream = null;
        /** @type {AudioContext | null} */
        this.context = null;
        /** @type {AudioWorkletNode | null} */
        this.node = null;
    }

    async start() {
        this.stream = await navigator.mediaDevices.getUserMedia({
            audio: { noiseSuppression: true, echoCancellation: true, channelCount: 1 },
        });
        this.context = new AudioContext();
        this.sampleRate = this.context.sampleRate;
        await this.context.audioWorklet.addModule(
            url("/speech/static/src/worklets/pcm_capture.js"),
        );
        this.node = new AudioWorkletNode(this.context, "speech-pcm-capture");
        this.node.port.onmessage = (event) => this.feed(event.data);
        this.context.createMediaStreamSource(this.stream).connect(this.node);
        if (this.context.state === "suspended") {
            await this.context.resume();
        }
    }

    /** @param {Float32Array} frame */
    feed(frame) {
        this.frames.push(frame);
        this.length += frame.length;
        this.quiet = rms(frame) < SILENCE_RMS ? this.quiet + frame.length : 0;
        const seconds = this.length / this.sampleRate;
        if (
            seconds >= MAX_CHUNK_S ||
            (seconds >= MIN_CHUNK_S && this.quiet >= PAUSE_S * this.sampleRate)
        ) {
            this.cut();
        }
    }

    cut() {
        if (!this.length) {
            return;
        }
        const samples = new Float32Array(this.length);
        let cursor = 0;
        for (const frame of this.frames) {
            samples.set(frame, cursor);
            cursor += frame.length;
        }
        const startS = this.offset / this.sampleRate;
        this.offset += samples.length;
        this.frames = [];
        this.length = 0;
        this.quiet = 0;
        if (rms(samples) < SILENCE_RMS) {
            return;
        }
        const pcm = downsample(samples, this.sampleRate, TARGET_RATE);
        this.onChunk({
            audio: toBase64(encodeWav(pcm, TARGET_RATE)),
            startS,
            durationS: samples.length / this.sampleRate,
            mimetype: "audio/wav",
        });
    }

    async stop() {
        this.node?.disconnect();
        this.cut();
        this.stream?.getTracks().forEach((track) => track.stop());
        await this.context?.close();
        this.node = null;
        this.stream = null;
        this.context = null;
    }
}
