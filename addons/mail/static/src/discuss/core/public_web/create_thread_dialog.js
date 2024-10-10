import { Component, useState } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { discussComponentRegistry } from "@mail/core/common/discuss_component_registry";
import { useService } from "@web/core/utils/hooks";
import { ImStatus } from "@mail/core/common/im_status";
import { ChannelInvitation } from "../common/channel_invitation";
import { _t } from "@web/core/l10n/translation";

export class CreateThreadDialog extends Component {
    static components = { ChannelInvitation, Dialog, ImStatus };
    static props = ["close", "name?", "onCompleted?", "types?"];
    static template = "mail.CreateThreadDialog";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.orm = useService("orm");
        this.discussCoreCommonService = useState(useService("discuss.core.common"));
        this.state = useState({
            autofocusInvitePeopleInput: 0,
            threadType: this.props.types?.[0] ?? "group",
            name: this.props.name.trim() ?? "",
            searchValue: "",
            searchResultCount: 0,
            isFetching: false,
            triedSubmitting: false,
        });
        this.invitePeopleState = useState({
            selectablePartners: [],
            selectedPartners: [],
        });
    }

    get dialogTitle() {
        if (this.props.types?.length === 1 && this.props.types[0] === "group") {
            return _t("Create Group Chat");
        }
        if (this.props.types?.length === 1 && this.props.types[0] === "channel") {
            return _t("Create Channel");
        }
        return _t("Create Conversation");
    }

    get selectedPartnersId() {
        return this.invitePeopleState.selectedPartners.map((partner) => partner.id);
    }

    async onClickConfirm() {
        this.state.triedSubmitting = true;
        if (!this.state.name) {
            return;
        }
        const partners_to = [...new Set([this.store.self.id, ...this.selectedPartnersId])];
        if (this.state.threadType === "group") {
            this.discussCoreCommonService.createGroupChat({ partners_to, name: this.state.name });
        } else if (this.state.threadType === "channel") {
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

    get threadTypeDescription() {
        if (this.state.threadType === "group") {
            return this.groupDescription;
        }
        return this.channelDescription;
    }

    get groupDescription() {
        return _t("Group chats are private and require an invitation to join");
    }

    get channelDescription() {
        return _t("Authorized users can find and join the channel by themselves");
    }

    onClickInvitePeople() {
        this.invitePeopleState.open = !this.invitePeopleState.open;
        if (this.invitePeopleState.open) {
            this.state.autofocusInvitePeopleInput++;
        }
    }
}

discussComponentRegistry.add("CreateThreadDialog", CreateThreadDialog);
