/* @odoo-module */

import { AttachmentList } from "@mail/core/common/attachment_list";
import { VoiceAnalyser } from "@mail/discuss/voice_message/common/voice_analyser";
import { patch } from "@web/core/utils/patch";

patch(AttachmentList, "discuss/voice_message/common", {
    components: { ...AttachmentList.components, VoiceAnalyser },
});
