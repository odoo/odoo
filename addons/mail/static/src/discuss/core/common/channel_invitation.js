/* @odoo-module */

import { ImStatus } from "@mail/core/common/im_status";
import { useMessaging, useStore } from "@mail/core/common/messaging_hook";

import { Component, onMounted, onWillStart, useRef, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ChannelInvitation extends Component {
    static components = { ImStatus };
    static defaultProps = { hasSizeConstraints: false };
    static props = ["hasSizeConstraints?", "thread", "close", "className?"];
    static template = "discuss.ChannelInvitation";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.notification = useService("notification");
        this.threadService = useState(useService("mail.thread"));
        this.personaService = useService("mail.persona");
        /** @type {import("@mail/core/common/suggestion_service").SuggestionService} */
        this.suggestionService = useService("mail.suggestion");
        this.ui = useService("ui");
        this.inputRef = useRef("input");
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
        const results = await this.messaging.orm.call("res.partner", "search_for_channel_invite", [
            this.searchStr,
            this.props.thread.id,
        ]);
        const Partners = results["partners"];
        const selectablePartners = [];
        for (const selectablePartner of Partners) {
            const partnerId = selectablePartner.id;
            const name = selectablePartner.name;
            const newPartner = this.personaService.insert({
                id: partnerId,
                name: name,
                type: "partner",
            });
            selectablePartners.push(newPartner);
        }
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
        if (this.state.selectedPartners.includes(partner)) {
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
            await this.threadService.startChat([
                this.props.thread.chatPartnerId,
                ...this.state.selectedPartners.map((partner) => partner.id),
            ]);
        } else {
            await this.messaging.orm.call(
                "discuss.channel",
                "add_members",
                [[this.props.thread.id]],
                {
                    partner_ids: this.state.selectedPartners.map((partner) => partner.id),
                }
            );
        }
        this.props.close();
    }

    get invitationButtonText() {
        if (this.props.thread.type === "channel") {
            return _t("Invite to Channel");
        } else if (this.props.thread.type === "group") {
            return _t("Invite to Group Chat");
        } else if (this.props.thread.type === "chat") {
            if (this.props.thread.chatPartnerId === this.store.self.id) {
                if (this.state.selectedPartners.length === 0) {
                    return _t("Invite");
                }
                if (this.state.selectedPartners.length === 1) {
                    const alreadyChat = Object.values(this.store.threads).some(
                        (thread) => thread.chatPartnerId === this.state.selectedPartners[0].id
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
}
