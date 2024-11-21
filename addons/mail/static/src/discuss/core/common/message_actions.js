import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { patch } from "@web/core/utils/patch";

const editAction = messageActionsRegistry.get("edit");

patch(editAction, {
    onClick(component) {
        const body = new DOMParser().parseFromString(component.message.body, "text/html");
        const mentionedChannelElements = body.querySelectorAll(".o_channel_redirect");
        component.message.mentionedChannelPromises = Array.from(mentionedChannelElements)
            .filter((el) => el.dataset.oeModel === "discuss.channel")
            .map(async (el) => {
                return component.store.Thread.getOrFetch({
                    id: el.dataset.oeId,
                    model: el.dataset.oeModel,
                });
            });
        return super.onClick(component);
    },
});
