import { Action } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";
import { propSignal } from "@mail/utils/common/hooks";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Component, t, useProps } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenuTabContextMenu extends Component {
    static template = "mail.MessagingMenuTabContextMenu";
    static components = { ActionList, Dropdown };

    setup() {
        super.setup();
        this.ancestors = useAncestors();
        this.store = useService("mail.store");
        this.props = useProps({ dropdownState: t.instanceOf(DropdownState) });
        this.actionsList = propSignal("actionsList", t.array(t.instanceOf(Action)));
        /** Anchor element, owned by the parent and bound here with `t-ref`. */
        this.anchorRef = propSignal("anchorRef", t.instanceOf(HTMLElement));
    }
}
