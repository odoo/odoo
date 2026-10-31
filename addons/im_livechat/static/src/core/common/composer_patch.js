import { Composer } from "@mail/core/common/composer";
import { patch } from "@web/core/utils/patch";

patch(Composer.prototype, {
    get showQuickVoiceStart() {
        return (
            this.props.composer.targetThread?.channel?.channel_type !== "livechat" &&
            super.showQuickVoiceStart
        );
    },
});
