import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { discussComponentRegistry } from "@mail/core/common/discuss_component_registry";
import { useService } from "@web/core/utils/hooks";
import { useSequential } from "@mail/utils/common/hooks";
import { ImStatus } from "@mail/core/common/im_status";

export class CreateThreadDialog extends Component {
    static components = { Dialog, ImStatus };
    static props = ["close", "name?", "onCompleted?"];
    static template = "mail.CreateThreadDialog";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.orm = useService("orm");
        this.sequential = useSequential();
        this.discussCoreCommonService = useState(useService("discuss.core.common"));
        this.suggestionService = useService("mail.suggestion");
        this.partnersSearch = useRef("partnersSearch");
        this.state = useState({
            threadType: "group",
            name: this.props.name.trim() ?? "",
            searchValue: "",
            searchResultCount: 0,
            isFetching: false,
            selectablePartners: [],
            selectedPartners: [],
            triedSubmitting: false,
        });
        onWillStart(() => {
            this.fetchPartnersToInvite();
        });
        useEffect(
            () => {
                this.fetchPartnersToInvite();
            },
            () => [this.state.searchValue]
        );
    }

    async fetchPartnersToInvite() {
        const results = await this.sequential(() =>
            this.orm.call("res.partner", "search_for_channel_invite", [this.state.searchValue])
        );
        if (!results) {
            return;
        }
        const { Persona: selectablePartners = [] } = this.store.insert(results.data);
        this.state.selectablePartners = this.suggestionService.sortPartnerSuggestions(
            selectablePartners,
            this.state.searchValue
        );
        this.state.searchResultCount = results.count;
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

    get selectedPartnersId() {
        return this.state.selectedPartners.map((partner) => partner.id);
    }

    async onClickConfirm() {
        this.state.triedSubmitting = true;
        const partners_to = [...new Set([this.store.self.id, ...this.selectedPartnersId])];
        if (this.state.threadType === "group") {
            this.discussCoreCommonService.createGroupChat({ partners_to, name: this.state.name });
        } else if (this.state.threadType === "channel") {
            if (!this.state.name) {
                return;
            }
            const data = await this.env.services.orm.call("discuss.channel", "channel_create", [
                this.state.name,
                this.store.internalUserGroupId,
            ]);
            const { Thread } = this.store.insert(data);
            const [channel] = Thread;
            await this.orm.call("discuss.channel", "add_members", [[channel.id]], {
                partner_ids: this.selectedPartnersId,
            });
            channel.open();
        }
        this.props.close();
        this.props.onCompleted?.();
    }
}

discussComponentRegistry.add("CreateThreadDialog", CreateThreadDialog);
