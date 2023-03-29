/* @odoo-module */

import { AttachmentService, attachmentService } from "@mail/core/common/attachment_service";
import { patch } from "@web/core/utils/patch";

patch(AttachmentService.prototype, "discuss/voice_message/common", {
    setup(env, services) {
        this._super(...arguments);
        /** @type {import("@mail/core/common/sound_effects_service").SoundEffects} */
        this.soundEffectsService = services["mail.sound_effects"];
    },
    update(attachment, data) {
        this._super(...arguments);
        if (data["duration"]) {
            attachment.duration = data["duration"];
        }
    },
    remove(attachment) {
        for (const thread of Object.values(this.store.threads)) {
            if (attachment.voiceDuration && attachment.id > 0) {
                thread.composer.hasVoice = false;
                this.soundEffectsService.activeAnalyser = null;
            }
        }
        this._super(...arguments);
    },
});

patch(attachmentService, "discuss/voice_message/common", {
    dependencies: [...attachmentService.dependencies, "mail.sound_effects"],
});
