/* @odoo-module */

import { AttachmentService, attachmentService } from "@mail/core/common/attachment_service";
import { patch } from "@web/core/utils/patch";

patch(AttachmentService.prototype, {
    setup(env, services) {
        super.setup(...arguments);
        /** @type {import("@mail/discuss/voice_message/common/voice_message_service").VoiceMessageService} */
        this.voiceMessageService = services["discuss.voice_message"];
    },
    remove(attachment) {
        if (attachment.isVoice && attachment.id > 0) {
            this.voiceMessageService.activePlayer = null;
        }
        super.remove(...arguments);
    },
});

patch(attachmentService, {
    dependencies: [...attachmentService.dependencies, "discuss.voice_message"],
});
