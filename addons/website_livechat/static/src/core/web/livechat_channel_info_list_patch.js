import { LivechatChannelInfoList } from "@im_livechat/core/web/livechat_channel_info_list";

import { compareDatetime } from "@mail/utils/common/misc";
import { computed } from "@odoo/owl";

import { toLocaleDateTimeString } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";

/** @type {LivechatChannelInfoList} */
const livechatChannelInfoListPatch = {
    setup() {
        super.setup();
        this.visitorPageViews = computed(() =>
            (this.props.thread.livechat_visitor_id?.last_track_ids ?? []).map((track) => {
                const parsedUrl = URL.parse(track.url);
                const isSafeUrl = ["http:", "https:"].includes(parsedUrl?.protocol);
                return {
                    url: isSafeUrl ? track.url : undefined,
                    title: track.page_id?.name || (isSafeUrl && parsedUrl.pathname) || track.url,
                    visitTime: toLocaleDateTimeString(track.visit_datetime),
                };
            })
        );
    },
    openVisitorPageViews() {
        return this.actionService.doAction("website.website_visitor_page_action", {
            additionalContext: {
                active_id: this.props.thread.livechat_visitor_id.id,
                search_default_type_url: 1,
            },
            newWindow: true,
        });
    },
    get recentConversations() {
        return (this.props.thread.livechat_visitor_id?.discuss_channel_ids ?? [])
            .filter((channel) => channel.notEq(this.props.thread.channel))
            .sort(
                (t1, t2) =>
                    compareDatetime(t2.last_interest_dt, t1.last_interest_dt) || t2.id - t1.id
            );
    },
    CLOSED_ON_TEXT(channel) {
        return toLocaleDateTimeString(channel.livechat_end_dt);
    },
};

patch(LivechatChannelInfoList.prototype, livechatChannelInfoListPatch);
