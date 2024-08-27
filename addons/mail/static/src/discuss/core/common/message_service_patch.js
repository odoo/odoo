import { MessageService } from "@mail/core/common/message_service";

import { patch } from "@web/core/utils/patch";
patch(MessageService.prototype, {
    async edit(
        message,
        body,
        attachments = [],
        { mentionedChannels = [], mentionedPartners = [] } = {}
    ) {
        const validChannels = (await Promise.all(message.mentionedChannelPromises)).filter(
            (channel) => channel !== undefined
        );
        const allChannels = this.store.Thread.insert([...validChannels, ...mentionedChannels]);
        super.edit(message, body, attachments, {
            mentionedChannels: allChannels,
            mentionedPartners,
        });
    },
});
