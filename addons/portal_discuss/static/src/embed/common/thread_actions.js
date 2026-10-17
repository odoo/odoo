import { externalThreadActions, threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/core/common/thread_actions";

import { patch } from "@web/core/utils/patch";
import { redirect } from "@web/core/utils/urls";

externalThreadActions.add("expand-discuss");

patch(threadActionsRegistry.get("expand-discuss"), {
    condition({ channel, owner, store }) {
        if (!channel || channel.isTransient) {
            return false;
        }
        if (store.self_user?.share === true && channel.channel_type === "livechat") {
            return channel.self_member_id && owner.props.chatWindow?.isOpen;
        }
        return (
            store.self_user?.share === false &&
            store.env.services.action &&
            super.condition(...arguments)
        );
    },
    onSelected({ channel, store }) {
        if (store.self_user?.share === true && channel?.channel_type === "livechat") {
            return redirect(`/discuss/channel/${channel.id}`);
        }
        return super.onSelected(...arguments);
    },
});
