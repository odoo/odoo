import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    /** @override */
    enterEditMode() {
        const body = new DOMParser().parseFromString(this.props.message.body, "text/html");
        const mentionedChannelElements = body.querySelectorAll(".o_channel_redirect");
        this.props.message.mentionedChannelPromises = Array.from(mentionedChannelElements)
            .filter((el) => el.dataset.oeModel === "discuss.channel")
            .map(async (el) => {
                return this.store.Thread.getOrFetch({
                    id: el.dataset.oeId,
                    model: el.dataset.oeModel,
                });
            });
        return super.enterEditMode();
    },
});
