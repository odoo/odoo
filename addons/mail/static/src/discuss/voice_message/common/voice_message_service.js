import { registry } from "@web/core/registry";

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
