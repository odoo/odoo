import { messageActionsRegistry } from "@mail/core/common/message_actions";
import { patch } from "@web/core/utils/patch";

patch(messageActionsRegistry.get("edit"), {
    async onClick(component) {
        const editOverride = document.querySelector(
            `[data-override_edit_message_id="${component.props.message.id}"] #ratingpopupcomposer`
        );
        if (!editOverride) {
            return await super.onClick(component);
        }
        new Modal(editOverride).show();
    },
});

patch(messageActionsRegistry.get("delete"), {
    async onClick(component) {
        if (component.message.model !== "slide.channel") {
            return await super.onClick(component);
        }
        const id = component.message.id;
        const bus = component.env.bus;
        const isDeleted = await super.onClick(component);
        if (isDeleted) {
            bus.trigger("WEBSITE_SLIDES:CHANNEL_DELETE_MESSAGE", { id });
        }
    },
});
