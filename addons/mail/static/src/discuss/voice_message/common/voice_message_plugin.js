import { StorePlugin } from "@mail/core/common/store_plugin";

import { Plugin, usePlugin } from "@odoo/owl";

import { loadBundle } from "@web/core/assets";
import { services } from "@web/core/services";
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

/** Records reach this plugin as `store.voiceMessage`. */
export class VoiceMessagePlugin extends Plugin {
    /** Started with the store it is reached from (see `StorePlugin`). */
    static sequence = 110;

    /** @type {import("@mail/discuss/voice_message/common/voice_player").VoicePlayer} */
    activePlayer = null;

    setup() {
        usePlugin(StorePlugin).voiceMessage = this;
    }
}

services.add(VoiceMessagePlugin);
