import { AttachmentList } from "@mail/core/common/attachment_list";
import { VoicePlayer } from "@mail/discuss/voice_message/common/voice_player";
import { patch } from "@web/core/utils/patch";

patch(AttachmentList, {
    components: { ...AttachmentList.components, VoicePlayer },
});

patch(AttachmentList.prototype, {
    openFileViewer(attachment) {
        if (!attachment.voice) {
            super.openFileViewer(attachment);
        }
    },
});
