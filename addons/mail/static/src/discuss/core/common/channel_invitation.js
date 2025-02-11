/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onMounted, onWillStart, useRef, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useSequential } from "@mail/utils/common/hooks";

export class ChannelInvitation extends Component {
    static components = { ImStatus, ActionPanel };
    static defaultProps = { hasSizeConstraints: false };
    static props = ["hasSizeConstraints?", "thread", "close", "className?"];
    static template = "discuss.ChannelInvitation";

    setup() {
        this.discussCoreCommonService = useState(useService("discuss.core.common"));
        this.orm = useService("orm");
        this.store = useState(useService("mail.store"));
        this.notification = useService("notification");
        this.threadService = useState(useService("mail.thread"));
        this.suggestionService = useService("mail.suggestion");
        this.ui = useService("ui");
        this.inputRef = useRef("input");
        this.sequential = useSequential();
        this.searchStr = "";
        this.state = useState({
            selectablePartners: [],
            selectedPartners: [],
            searchResultCount: 0,
        });
        onWillStart(() => {
            if (this.store.user) {
                this.fetchPartnersToInvite();
            }
        });
        onMounted(() => {
            if (this.store.user) {
                this.inputRef.el.focus();
            }
        });
    }

    async fetchPartnersToInvite() {
        const results = await this.sequential(() =>
            this.orm.call("res.partner", "search_for_channel_invite", [
                this.searchStr,
                this.props.thread.id,
            ])
        );
        if (!results) {
            return;
        }
        const selectablePartners = this.store.Persona.insert(results.partners);
        this.state.selectablePartners = this.suggestionService.sortPartnerSuggestions(
            selectablePartners,
            this.searchStr,
            this.props.thread
        );
        this.state.searchResultCount = results["count"];
    }

    onInput() {
        this.searchStr = this.inputRef.el.value;
        this.fetchPartnersToInvite();
    }

    onClickSelectablePartner(partner) {
        if (partner.in(this.state.selectedPartners)) {
            const index = this.state.selectedPartners.indexOf(partner);
            if (index !== -1) {
                this.state.selectedPartners.splice(index, 1);
            }
            return;
        }
        this.state.selectedPartners.push(partner);
    }

    onClickSelectedPartner(partner) {
        const index = this.state.selectedPartners.indexOf(partner);
        this.state.selectedPartners.splice(index, 1);
    }

    onFocusInvitationLinkInput(ev) {
        ev.target.select();
    }

    async onClickCopy(ev) {
        await navigator.clipboard.writeText(this.props.thread.invitationLink);
        this.notification.add(_t("Link copied!"), { type: "success" });
    }

    async onClickInvite() {
        if (this.props.thread.type === "chat") {
            await this.discussCoreCommonService.startChat([
                this.props.thread.chatPartner?.id,
                ...this.state.selectedPartners.map((partner) => partner.id),
            ]);
        } else {
            await this.orm.call("discuss.channel", "add_members", [[this.props.thread.id]], {
                partner_ids: this.state.selectedPartners.map((partner) => partner.id),
            });
        }
        this.props.close();
    }

    get invitationButtonText() {
        if (this.props.thread.type === "channel") {
            return _t("Invite to Channel");
        } else if (this.props.thread.type === "group") {
            return _t("Invite to Group Chat");
        } else if (this.props.thread.type === "chat") {
            if (this.props.thread.chatPartner?.eq(this.store.self)) {
                if (this.state.selectedPartners.length === 0) {
                    return _t("Invite");
                }
                if (this.state.selectedPartners.length === 1) {
                    const alreadyChat = Object.values(this.store.Thread.records).some((thread) =>
                        thread.chatPartner?.eq(this.state.selectedPartners[0])
                    );
                    if (alreadyChat) {
                        return _t("Go to conversation");
                    }
                    return _t("Start a Conversation");
                }
            }
            return _t("Create Group Chat");
        }
        return _t("Invite");
    }

    get title() {
        return _t("Invite people");
    }
}
