import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { patch } from "@web/core/utils/patch";

patch(messageActionsRegistry.get("edit"), {
    async onSelected(component) {
        const editOverride = document.querySelector(
            `[data-message-id="${component.message.id}"] #ratingpopupcomposer`
        );
        if (!editOverride) {
            return await super.onSelected(component);
        }
        new Modal(editOverride).show();
    },
});

patch(messageActionsRegistry.get("delete"), {
    async onSelected(component) {
        const isDeleted = await super.onSelected(component);
        if (isDeleted && component.message.model === "slide.channel") {
            component.store.env.bus.trigger("WEBSITE_SLIDES:CHANNEL_DELETE_MESSAGE", {
                id: component.message.id,
            });
        }
        return isDeleted;
    },
});
