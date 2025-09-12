import { LivechatChannelInfoList } from "@im_livechat/core/web/livechat_channel_info_list";
import { formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

/** @type {import("models").ChannelMember} */
const livechatChannelInfoListPatch = {
    get recentConversations() {
        return (this.props.thread.livechat_visitor_id?.discuss_channel_ids ?? [])
            .filter((channel) => channel.notEq(this.props.thread))
            .sort((t1, t2) => {
                if (t1.livechat_end_dt && !t2.livechat_end_dt) {
                    return 1;
                }
                if (!t1.livechat_end_dt && t2.livechat_end_dt) {
                    return -1;
                }
                return t1.livechat_end_dt.diff(t2.livechat_end_dt) > 0 ? -1 : 1;
            });
    },
    CLOSED_ON_TEXT(thread) {
        return _t("(closed on: %(date)s)", { date: formatDateTime(thread.livechat_end_dt) });
    },
    get countryLanguageLabel() {
        return _t("Country & Language");
    },
};

patch(LivechatChannelInfoList.prototype, livechatChannelInfoListPatch);
