import { DiscussCommandPalette } from "@mail/discuss/core/web/discuss_command_palette";
import { patch } from "@web/core/utils/patch";

patch(DiscussCommandPalette.prototype, {
    async openThread(thread) {
        super.openThread(...arguments);
        if (thread?.channel_type === "livechat") {
            const channel = await this.store.Thread.getOrFetch(thread);
            channel.open();
        }
    },
});
