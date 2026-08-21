import { Action } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";
import { Component, t, useProps } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenuItemContextMenu extends Component {
    static template = "mail.MessagingMenuItemContextMenu";
    static components = { ActionList, Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            actionsList: t.signal(
                t.array(t.or([t.instanceOf(Action), t.array(t.instanceOf(Action))]))
            ),
            /** Anchor element, owned by the parent and bound here with `t-ref`. */
            anchorRef: t.signal(t.instanceOf(HTMLElement), { settable: true }),
            dropdownState: t.instanceOf(DropdownState),
        });
    }
}
