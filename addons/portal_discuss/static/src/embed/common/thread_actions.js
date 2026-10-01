import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/core/common/thread_actions";
import { visitorActions } from "@im_livechat/core/common/thread_actions_patch";

import { patch } from "@web/core/utils/patch";
import { redirect } from "@web/core/utils/urls";

visitorActions.add("expand-discuss");

patch(threadActionsRegistry.get("expand-discuss"), {
    condition({ channel, owner, store }) {
        if (store.self_user?.share === true && channel?.channel_type === "livechat") {
            return !channel.isTransient && channel.self_member_id && owner.props.chatWindow?.isOpen;
        }
        return super.condition(...arguments);
    },
    onSelected({ channel, store }) {
        if (store.self_user?.share === true && channel?.channel_type === "livechat") {
            return redirect(`/discuss/channel/${channel.id}`);
        }
        return super.onSelected(...arguments);
    },
});
