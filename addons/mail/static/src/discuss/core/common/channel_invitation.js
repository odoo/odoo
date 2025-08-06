import { ImStatus } from "@mail/core/common/im_status";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onMounted, onWillStart, useEffect, useRef, useState } from "@odoo/owl";

import { useSequential } from "@mail/utils/common/hooks";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class ChannelInvitation extends Component {
    static components = { ImStatus, ActionPanel };
    static defaultProps = { hasSizeConstraints: false };
    static props = [
        "autofocus?",
        "hasSizeConstraints?",
        "thread?",
        "close?",
        "className?",
        "state?",
    ];
    static template = "discuss.ChannelInvitation";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.rtc = useService("discuss.rtc");
        this.notification = useService("notification");
        this.suggestionService = useService("mail.suggestion");
        this.ui = useService("ui");
        this.inputRef = useRef("input");
        this.sequential = useSequential();
        this.state = useState({
            selectablePartners: [],
            selectedPartners: [],
            searchResultCount: 0,
            searchStr: "",
        });
        this.debouncedFetchPartnersToInvite = useDebounced(
            this.fetchPartnersToInvite.bind(this),
            250
        );
        onWillStart(() => {
            if (this.store.self_partner) {
                this.fetchPartnersToInvite();
            }
        });
        onMounted(() => {
            if (this.store.self_partner && this.props.thread) {
                this.inputRef.el.focus();
            }
        });
        useEffect(
            () => {
                if (this.props.autofocus) {
                    this.inputRef.el?.focus();
                }
            },
            () => [this.props.autofocus]
        );
    }

    get selectablePartners() {
        return this.props.state?.selectablePartners ?? this.state.selectablePartners;
    }

    set selectablePartners(partners) {
        if (this.props.state?.selectablePartners) {
            this.props.state.selectablePartners = partners;
        } else {
            this.state.selectablePartners = partners;
        }
    }

    get selectedPartners() {
        return this.props.state?.selectedPartners ?? this.state.selectedPartners;
    }

    set selectedPartners(partners) {
        if (this.props.state?.selectedPartners) {
            this.props.state.selectedPartners = partners;
        } else {
            this.state.selectedPartners = partners;
        }
    }

    get searchStr() {
        return this.props.state?.searchStr ?? this.state.searchStr;
    }

    set searchStr(newSearchStr) {
        if (this.props.state?.searchStr !== undefined) {
            this.props.state.searchStr = newSearchStr;
        } else {
            this.state.searchStr = newSearchStr;
        }
    }

    get showingResultNarrowText() {
        return _t(
            "Showing %(result_count)s results out of %(total_count)s. Narrow your search to see more choices.",
            {
                result_count: this.selectablePartners.length,
                total_count: this.state.searchResultCount,
            }
        );
    }

    get searchPlaceholder() {
        return this.props.state?.searchPlaceholder ?? _t("Search people to invite");
    }

    async fetchPartnersToInvite() {
        const results = await this.sequential(() =>
            this.orm.call("res.partner", "search_for_channel_invite", [
                this.searchStr,
                this.props.thread?.id ?? false,
            ])
        );
        if (!results) {
            return;
        }
        const { "res.partner": selectablePartners = [] } = this.store.insert(results.data);
        this.selectablePartners = this.suggestionService.sortPartnerSuggestions(
            selectablePartners,
            this.searchStr,
            this.props.thread
        );
        this.state.searchResultCount = results["count"];
    }

    onInput() {
        this.searchStr = this.inputRef.el.value;
        this.debouncedFetchPartnersToInvite();
    }

    onClickSelectablePartner(partner) {
        if (partner.in(this.selectedPartners)) {
            const index = this.selectedPartners.indexOf(partner);
            if (index !== -1) {
                this.selectedPartners.splice(index, 1);
            }
            return;
        }
        this.selectedPartners.push(partner);
    }

    onClickSelectedPartner(partner) {
        const index = this.selectedPartners.indexOf(partner);
        this.selectedPartners.splice(index, 1);
    }

    onFocusInvitationLinkInput(ev) {
        ev.target.select();
    }

    async onClickCopy(ev) {
        await navigator.clipboard.writeText(this.props.thread.invitationLink);
        this.notification.add(_t("Link copied!"), { type: "success" });
    }

    async onClickInvite() {
        if (this.props.thread.channel_type === "chat") {
            const partnerIds = this.selectedPartners.map((partner) => partner.id);
            if (this.props.thread.correspondent) {
                partnerIds.unshift(this.props.thread.correspondent.persona.id);
            }
            await this.store.startChat(partnerIds);
        } else {
            await this.orm.call("discuss.channel", "add_members", [[this.props.thread.id]], {
                partner_ids: this.selectedPartners.map((partner) => partner.id),
                invite_to_rtc_call: this.rtc.state.channel?.eq(this.props.thread),
            });
        }
        if (this.props.close) {
            this.props.close();
        } else {
            this.state.selectablePartners = this.state.selectablePartners.filter(
                (partner) => !this.selectedPartners.includes(partner)
            );
            this.state.selectedPartners = [];
        }
    }

    get invitationButtonText() {
        if (!this.props.thread) {
            return "";
        }
        if (this.props.thread.channel_type === "channel") {
            return _t("Invite");
        } else if (this.props.thread.channel_type === "group") {
            return _t("Invite to Group Chat");
        } else if (this.props.thread.channel_type === "chat") {
            if (this.props.thread.correspondent?.persona.eq(this.store.self)) {
                if (this.selectedPartners.length === 0) {
                    return _t("Invite");
                }
                if (this.selectedPartners.length === 1) {
                    const alreadyChat = Object.values(this.store.Thread.records).some((thread) =>
                        thread.correspondent?.persona.eq(this.selectedPartners[0])
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
