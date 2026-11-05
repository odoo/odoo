import { Action } from "@mail/core/common/action";
import { ActionList } from "@mail/core/common/action_list";
<<<<<<< 8dd23357410ce4592702c0eb65e46096ce62e456
import { propStatic, usePropsPlus } from "@mail/utils/common/hooks";
import { useAncestors } from "@mail/core/common/ancestor_plugin";
||||||| 8ea8dd69ebc899afa567040fc31379aa48ddf320
import { propSignal } from "@mail/utils/common/hooks";
=======
import { IsolatedDropdown } from "@mail/core/public_web/messaging_menu/isolated_dropdown";
import { propSignal } from "@mail/utils/common/hooks";
>>>>>>> 03078485c59c6146eb9358c2dea001dd01204bf0

import { Component, t } from "@odoo/owl";

import { DropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";

export class MessagingMenuItemContextMenu extends Component {
    static template = "mail.MessagingMenuItemContextMenu";
    static components = { ActionList, IsolatedDropdown };

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
