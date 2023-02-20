/* @odoo-module */

import { Component, useRef, useState, onMounted, onWillStart } from "@odoo/owl";
import { useMessaging, useStore } from "@mail/new/core/messaging_hook";
import { ImStatus } from "./im_status";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ChannelInvitationForm extends Component {
    static components = { ImStatus };
    static props = ["thread", "close?", "chatState?"];
    static template = "mail.channel_invitation_form";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.notification = useService("notification");
        this.threadService = useState(useService("mail.thread"));
        this.personaService = useService("mail.persona");
        this.inputRef = useRef("input");
        this.searchStr = "";
        this.state = useState({
            selectablePartners: [],
            selectedPartners: [],
            searchResultCount: 0,
        });
        onWillStart(() => this.fetchPartnersToInvite());
        onMounted(() => {
            this.inputRef.el.focus();
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
        this.state.selectablePartners = selectablePartners;
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
            const partners_to = [
                this.store.self.id,
                this.props.thread.chatPartnerId,
                ...this.state.selectedPartners.map((partner) => partner.id),
            ];
            await this.threadService.createGroupChat({ partners_to });
        } else if (["channel", "group"].includes(this.props.thread.type)) {
            await this.messaging.orm.call("mail.channel", "add_members", [[this.props.thread.id]], {
                partner_ids: this.state.selectedPartners.map((partner) => partner.id),
            });
        }
        if (this.env.isSmall) {
            this.props.chatState.activeMode = "";
        } else {
            this.props.close();
        }
    }

    get invitationButtonText() {
        if (this.props.thread.type === "channel") {
            return _t("Invite to Channel");
        } else if (this.props.thread.type === "group") {
            return _t("Invite to Group Chat");
        } else if (this.props.thread.type === "chat") {
            return _t("Create Group Chat");
        }
        return _t("Invite");
    }
}
