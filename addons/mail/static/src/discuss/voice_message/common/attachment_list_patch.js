import { AttachmentList } from "@mail/core/common/attachment_list";
import { VoicePlayer } from "@mail/discuss/voice_message/common/voice_player";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

patch(AttachmentList, {
    components: {
        ...AttachmentList.components,
        Dropdown,
        DropdownItem,
        VoicePlayer,
    },
});

patch(AttachmentList.prototype, {
    getPlaybackRate(attachment) {
        return attachment.voice_ids?.[0]?.playbackRate ?? 1;
    },

    setup() {
        super.setup();
        this.voiceMessageService = useService("discuss.voice_message");
    },

    setPlaybackRate(attachment, rate) {
        const playbackRate = parseFloat(rate);
        if (attachment.voice_ids?.[0]) {
            attachment.voice_ids[0].playbackRate = playbackRate;
            if (this.voiceMessageService?.activePlayer?.props.attachment === attachment) {
                this.voiceMessageService.activePlayer.applyPlaybackRate();
            }
        }
    },
});
