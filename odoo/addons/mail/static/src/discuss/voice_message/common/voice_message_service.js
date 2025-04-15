/* @odoo-module */

import { loadBundle } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { memoize } from "@web/core/utils/functions";

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
