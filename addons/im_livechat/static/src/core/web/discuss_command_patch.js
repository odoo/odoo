import { DiscussCommand } from "@mail/discuss/core/public_web/discuss_command_palette";

import { patch } from "@web/core/utils/patch";

/** @type {DiscussCommand} */
const discussCommandComponentPatch = {
    get email() {
        return this.props.channel?.livechatVisitorMember?.persona.email ?? super.email;
    },
    get lastMessagePreview() {
        return this.props.channel?.channel_type === "livechat"
            ? this.props.channel.newestPersistentOfAllMessage?.previewText
            : undefined;
    },
};
patch(DiscussCommand.prototype, discussCommandComponentPatch);
