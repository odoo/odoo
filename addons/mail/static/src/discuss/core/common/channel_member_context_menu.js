import { ActionList } from "@mail/core/common/action_list";
import { useChannelMemberActions } from "@mail/discuss/core/common/channel_member_actions";
import { propSignal } from "@mail/utils/common/hooks";

import { Component, t, useProps } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";

export class ChannelMemberContextMenu extends Component {
    static template = "mail.ChannelMemberContextMenu";
    static components = { ActionList, Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            dropdownState: t.instanceOf(DropdownState),
            member: t.instanceOf(this.store["discuss.channel.member"]),
        });
        /** Anchor element, owned by the parent and bound here with `t-ref`. */
        this.anchorRef = propSignal("anchorRef", t.instanceOf(HTMLElement));
        this.memberActions = useChannelMemberActions({ member: () => this.props.member });
    }
}
