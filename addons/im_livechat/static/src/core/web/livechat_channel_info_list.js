import { TranscriptSender } from "@im_livechat/core/common/transcript_sender";
import { ExpertiseTagsAutocomplete } from "@im_livechat/core/web/expertise_tags_autocomplete";

import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { prettifyMessageContent } from "@mail/utils/common/format";
import { compareDatetime } from "@mail/utils/common/misc";

import { Component, useEffect } from "@odoo/owl";

import { startUrl } from "@web/core/browser/router";
import { toLocaleDateTimeString } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

export class LivechatChannelInfoList extends Component {
    static components = { ActionPanel, ExpertiseTagsAutocomplete, TranscriptSender };
    static template = "im_livechat.LivechatChannelInfoList";
    static props = ["close?", "thread"];

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.toLocaleDateTimeString = toLocaleDateTimeString;
        useEffect(() => {
            if (this.props.thread.hasFetchedLivechatSessionData) {
                return;
            }
            this.store.fetchStoreData("/im_livechat/session/data", {
                channel_id: this.props.thread.id,
            });
            this.props.thread.hasFetchedLivechatSessionData = true;
        });
    }

    get expectAnswerSteps() {
        return this.props.thread.messages
            .filter((m) => m.chatbotStep?.expectAnswer && m.chatbotStep.answer)
            .map((m) => m.chatbotStep);
    }

    onBlurNote() {
        prettifyMessageContent(this.props.thread.channel.livechatNoteText).then((note) => {
            rpc("/im_livechat/session/update_note", {
                channel_id: this.props.thread.channel.id,
                note,
            });
        });
    }

    async openVisitorProfile() {
        await this.store.chatHub.initPromise;
        if (this.ui.isSmall) {
            this.props.thread.channel.chatWindow?.fold();
        } else {
            this.props.thread.channel.openChatWindow({ focus: true });
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: this.props.thread.channel.livechatVisitorMember.partner_id.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    get visitorProfileURL() {
        const visitorMember = this.props.thread?.channel?.livechatVisitorMember;
        if (visitorMember?.partner_id) {
            return url(`/${startUrl()}/res.partner/${visitorMember.partner_id.id}`);
        }
        return undefined;
    }

    get recentChannels() {
        return (this.props.thread.channel?.recent_channel_ids ?? []).sort(
            (c1, c2) =>
                !c2.livechat_end_dt - !c1.livechat_end_dt ||
                compareDatetime(c2.last_interest_dt, c1.last_interest_dt) ||
                c2.id - c1.id
        );
    }

    get hasMoreRecentChannels() {
        return (
            this.props.thread.channel?.recent_channels_count >
            this.props.thread.channel?.recent_channel_ids.length
        );
    }

    async openRecentChannels(ev, isMiddleClick) {
        const action = await this.orm.call("discuss.channel", "action_recent_channels", [
            this.props.thread.channel.id,
        ]);
        this.actionService.doAction(action, { newWindow: isMiddleClick });
    }
}
