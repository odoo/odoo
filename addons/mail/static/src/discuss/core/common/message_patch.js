import { Message } from "@mail/core/common/message";
import { createDocumentFragmentFromContent } from "@mail/utils/common/html";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    /** @override */
    enterEditMode() {
        const body = createDocumentFragmentFromContent(this.props.message.body);
        const mentionedChannelElements = body.querySelectorAll(".o_channel_redirect");
        this.props.message.mentionedChannelPromises = Array.from(mentionedChannelElements)
            .filter((el) => el.dataset.oeModel === "discuss.channel")
            .map(async (el) =>
                this.store.Thread.getOrFetch({
                    id: el.dataset.oeId,
                    model: el.dataset.oeModel,
                })
            );
        return super.enterEditMode();
    },
});
