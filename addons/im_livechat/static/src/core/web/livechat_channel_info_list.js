import { TranscriptSender } from "@im_livechat/core/common/transcript_sender";
import { ExpertiseTagsAutocomplete } from "@im_livechat/core/web/expertise_tags_autocomplete";

import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { prettifyMessageContent } from "@mail/utils/common/format";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Component, signal, t, useEffect, useProps } from "@odoo/owl";

import { startUrl } from "@web/core/browser/router";
import { loadLanguages } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useService } from "@web/core/utils/hooks";
import { url } from "@web/core/utils/urls";

export class LivechatChannelInfoList extends Component {
    static components = { ActionPanel, ExpertiseTagsAutocomplete, SelectMenu, TranscriptSender };
    static template = "im_livechat.LivechatChannelInfoList";
    props = useProps({
        close: t.function().optional(),
        thread: t.object(),
    });
    /** Installed languages, as choices of the language select menu. */
    languages = signal([]);

    setup() {
        super.setup();
        this.ancestors = useAncestors();
        this.actionService = useService("action");
        this.store = useService("mail.store");
        this.ui = useService("ui");
        if (this.store.has_access_livechat) {
            loadLanguages(useService("orm")).then((languages) =>
                this.languages.set(languages.map(([value, label]) => ({ value, label })))
            );
        }
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

    get answeredChatbotMessages() {
        return this.props.thread.channel.sortedChatbotMessages.filter(
            (m) => m.expectAnswer && m.answer
        );
    }

    onBlurNote() {
        prettifyMessageContent(this.props.thread.channel.livechatNoteText).then((note) => {
            rpc("/im_livechat/session/update_note", {
                channel_id: this.props.thread.channel.id,
                note,
            });
        });
    }

    /** @param {string} langCode */
    onSelectLang(langCode) {
        rpc("/im_livechat/session/update_lang", {
            channel_id: this.props.thread.channel.id,
            lang_code: langCode,
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
}
