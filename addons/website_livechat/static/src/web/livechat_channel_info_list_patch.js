import { LivechatChannelInfoList } from "@im_livechat/core/web/livechat_channel_info_list";

import { compareDatetime } from "@mail/utils/common/misc";

import { formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {LivechatChannelInfoList} */
const livechatChannelInfoListPatch = {
    get recentConversations() {
        return (this.props.thread.livechat_visitor_id?.discuss_channel_ids ?? [])
            .filter((channel) => channel.notEq(this.props.thread))
            .sort(
                (t1, t2) =>
                    compareDatetime(t2.last_interest_dt, t1.last_interest_dt) || t2.id - t1.id
            );
    },
    CLOSED_ON_TEXT(thread) {
        return _t("(closed on: %(date)s)", { date: formatDateTime(thread.livechat_end_dt) });
    },
};

patch(LivechatChannelInfoList.prototype, livechatChannelInfoListPatch);
