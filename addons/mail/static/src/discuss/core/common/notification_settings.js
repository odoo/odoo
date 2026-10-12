import { Component, signal, t, useProps } from "@odoo/owl";
import { ActionPanel } from "@mail/discuss/core/common/action_panel";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { DROPDOWN_NESTING } from "@web/core/dropdown/_behaviours/dropdown_nesting";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useHover } from "@mail/utils/common/hooks";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

export class NotificationSettings extends Component {
    static components = { ActionPanel, Dropdown, DropdownItem };
    static template = "discuss.NotificationSettings";

    muteButtonRef = signal.ref();
    muteMenuRef = signal.ref();

    setup() {
        this.ancestors = useAncestors();
        this.store = useService("mail.store");
        this.props = useProps({
            channel: t.instanceOf(this.store["discuss.channel"]),
            close: t.function([t.instanceOf(MouseEvent)]).optional(),
        });
        this.dialog = useService("dialog");
        this.ui = useService("ui");
        this.DROPDOWN_NESTING = DROPDOWN_NESTING;
        this.muteConversationDropdownState = useDropdownState();
        this.muteConversationHover = useHover([this.muteButtonRef, this.muteMenuRef], {
            onHover: () => (this.muteConversationDropdownState.isOpen = true),
            onAway: () => (this.muteConversationDropdownState.isOpen = false),
        });
    }

    setMute(minutes) {
        this.store.settings.setMuteDuration(minutes, this.props.channel);
        this.props.close?.();
    }
}
