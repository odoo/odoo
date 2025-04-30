import { parseEmail } from "@mail/utils/common/format";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { useService } from "@web/core/utils/hooks";
import { isEmail } from "@web/core/utils/strings";

import { Component, useExternalListener, useRef, useState } from "@odoo/owl";
/**
 * This class represents the popover opened when we detect that one of our recipients is missing an email
 * address in the RecipientsInput. It allows the user to correct this error and update the partner
 * with an email address.
 */
export class RecipientsInputTagsListPopover extends Component {
    static props = {
        tagToUpdate: { type: Object },
        onUpdateTag: { type: Function },
        close: { type: Function },
    };
    static template = "mail.RecipientsInputTagsListPopover";

    setup() {
        this.orm = useService("orm");
        this.state = useState({ value: "" });
        this.popoverRef = useRef("tagsListPopoverRef");
        useExternalListener(window, "click", (ev) => {
            if (!this.popoverRef.el?.contains(ev.target)) {
                this.discardTag();
            }
        });
    }

    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        this.state.error = false;
        if (hotkey === "enter") {
            this.updateTag();
        }
        if (hotkey === "escape") {
            this.discardTag();
        }
    }

    updateTag() {
        if (!this.isValidEmail) {
            this.state.error = true;
            return;
        }
        this.props.onUpdateTag(this.state.value);
        this.props.close();
    }

    discardTag() {
        this.props.tagToUpdate.onDelete();
        this.props.close();
    }

    get isValidEmail() {
        const value = parseEmail(this.state.value);
        const name = value ? value[0] : "";
        return isEmail(name);
    }
}
