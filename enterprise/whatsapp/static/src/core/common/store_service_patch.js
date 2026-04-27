import { Store } from "@mail/core/common/store_service";
import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    async getMessagePostParams({ thread }) {
        const params = await super.getMessagePostParams(...arguments);

        if (thread.channel_type === "whatsapp") {
            params.post_data.message_type = "whatsapp_message";
        }
        return params;
    },

    async openWhatsAppChannel(id, name) {
        const thread = this.Thread.insert({
            channel_type: "whatsapp",
            id,
            model: "discuss.channel",
            name,
        });
        if (!thread.avatarCacheKey) {
            thread.avatarCacheKey = "hello";
        }
        if (!thread.hasSelfAsMember) {
            const data = await this.env.services.orm.call(
                "discuss.channel",
                "whatsapp_channel_join_and_pin",
                [[id]]
            );
            this.insert(data);
        } else if (!thread.is_pinned) {
            thread.pin();
        }
        thread.open();
    },
});
