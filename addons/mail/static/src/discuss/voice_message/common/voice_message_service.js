import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";
import { clamp } from "@web/core/utils/numbers";

const loader = {
    loadLamejs: memoize(() => loadBundle("mail.assets_lamejs")),
};

export async function loadLamejs() {
    try {
        await loader.loadLamejs();
    } catch {
        // Could be intentional (tour ended successfully while lamejs still loading)
    }
}

/**
 * @param {number} seconds
 * @returns {string} formatted as "mm : ss"
 */
export function formatVoiceTime(seconds) {
    const second = Math.floor(seconds % 60);
    const minute = Math.floor(seconds / 60);
    return `${String(minute).padStart(2, "0")} : ${String(second).padStart(2, "0")}`;
}

/**
 * @param {Float32Array} samples
 * @returns {number} the loudest sample, as an absolute value
 */
export function getVolumePeak(samples) {
    let volumePeak = 0;
    for (let index = 0; index < samples.length; index++) {
        const volume = Math.abs(samples[index]);
        if (volume > volumePeak) {
            volumePeak = volume;
        }
    }
    return volumePeak;
}

// Used to turn a sample peak into a bar height, from 0 (silence) to 1 (loudest).
// Decibels follow how the ear hears: 20 * log10(peak), so a peak of 1 is 0 dB and 0.01 is -40 dB.
// Below -50 dB is treated as room noise and stays flat, while a whisper (around -35 dB) still shows.
const SILENCE_DECIBELS = -50;

/**
 * @param {number} volumePeak
 * @returns {number} the loudness of the peak, from 0 (-50 dB or quieter) to 1 (0 dB)
 */
export function getVolumeLevel(volumePeak) {
    return clamp(1 - (20 * Math.log10(volumePeak)) / SILENCE_DECIBELS, 0, 1);
}

export class VoiceMessageService {
    constructor(env) {
        /** @type {import("@mail/discuss/voice_message/common/voice_player").VoicePlayer} */
        this.activePlayer = null;
    }
}

export const voiceMessageService = {
    start(env) {
        return new VoiceMessageService(env);
    },
};

registry.category("services").add("discuss.voice_message", voiceMessageService);
