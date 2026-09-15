import {
    THREAD_ACTION_IDS,
    ThreadAction,
    threadActionsRegistry,
} from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ThreadAction.prototype, {
    _condition({ action, channel, store }) {
        const visitorActions = [
            THREAD_ACTION_IDS.FOLD_CHAT_WINDOW,
            THREAD_ACTION_IDS.CLOSE,
            "restart",
            THREAD_ACTION_IDS.CALL_SETTINGS,
            THREAD_ACTION_IDS.MEETING_CHAT,
            THREAD_ACTION_IDS.LEAVE,
            THREAD_ACTION_IDS.NOTIFICATION_SETTINGS,
        ];
        if (
            channel?.channel_type === "livechat" &&
            store.self_user?.share !== false &&
            !visitorActions.includes(action.id)
        ) {
            return false;
        }
        return super._condition(...arguments);
    },

    _name({ action, channel }) {
        if (action.id === THREAD_ACTION_IDS.LEAVE && channel?.livechatShouldAskLeaveConfirmation) {
            return _t("Close Conversation");
        }
    },
});

patch(threadActionsRegistry.get(THREAD_ACTION_IDS.NOTIFICATION_SETTINGS), {
    condition({ channel }) {
        if (channel?.channel_type === "livechat") {
            return super.condition(...arguments) && !channel.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});

patch(threadActionsRegistry.get(THREAD_ACTION_IDS.CAMERA_CALL), {
    condition({ channel }) {
        if (channel?.channel_type === "livechat") {
            return super.condition(...arguments) && !channel.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});

patch(threadActionsRegistry.get(THREAD_ACTION_IDS.CALL), {
    condition({ channel }) {
        if (channel?.channel_type === "livechat") {
            return super.condition(...arguments) && !channel.livechat_end_dt;
        }
        return super.condition(...arguments);
    },
});
