import { AttachmentList } from "@mail/core/common/attachment_list";
import { VoicePlayer } from "@mail/discuss/voice_message/common/voice_player";
import { VoicePlayerControls } from "@mail/discuss/voice_message/common/voice_player_controls";

import { patch } from "@web/core/utils/patch";

patch(AttachmentList, {
    components: {
        ...AttachmentList.components,
        VoicePlayer,
        VoicePlayerControls,
    },
});

patch(AttachmentList.prototype, {
    getPreviewAttClass(attachment) {
        return {
            ...super.getPreviewAttClass(attachment),
            o_image: !attachment.voice,
        };
    },
});
