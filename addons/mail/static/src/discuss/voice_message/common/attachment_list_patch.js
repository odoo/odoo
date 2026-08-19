import { AttachmentList } from "@mail/core/common/attachment_list";
import { VoicePlaybackRate } from "@mail/discuss/voice_message/common/voice_playback_rate";
import { VoicePlayer } from "@mail/discuss/voice_message/common/voice_player";

import { patch } from "@web/core/utils/patch";

patch(AttachmentList, {
    components: {
        ...AttachmentList.components,
        VoicePlaybackRate,
        VoicePlayer,
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
