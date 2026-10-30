import { Action } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";
import { propStatic, usePropsPlus } from "@mail/utils/common/hooks";
import { useAncestors } from "@mail/core/common/ancestor_plugin";

import { Component, t } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenuItemContextMenu extends Component {
    static template = "mail.MessagingMenuItemContextMenu";
    static components = { ActionList, Dropdown };

    setup() {
        super.setup();
        this.ancestors = useAncestors();
        this.store = useService("mail.store");
        this.props = usePropsPlus({
            actionsList: propStatic(
                t.signal(t.array(t.or([t.instanceOf(Action), t.array(t.instanceOf(Action))])))
            ),
            /** Anchor element, owned by the parent and bound here with `t-ref`. */
            anchorRef: propStatic(t.signal(t.instanceOf(HTMLElement))),
            dropdownState: t.instanceOf(DropdownState),
            /** @see import("@mail/core/common/action_list").ActionPanelContainer */
            panelContainer: t.function().optional(),
        });
    }
}
