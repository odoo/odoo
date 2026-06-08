import { useRef } from "@web/owl2/utils";
import { parseEmail } from "@mail/utils/common/format";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { useService } from "@web/core/utils/hooks";
import { isEmail } from "@web/core/utils/strings";

import { Component, props, signal, types, useListener } from "@odoo/owl";
/**
 * This class represents the popover opened when we detect that one of our recipients is missing an email
 * address in the RecipientsInput. It allows the user to correct this error and update the partner
 * with an email address.
 */
export class RecipientsInputTagsListPopover extends Component {
    static template = "mail.RecipientsInputTagsListPopover";

    setup() {
        this.props = props({
            close: types.function([]),
            onUpdateTag: types.function([types.string()]),
            tagToUpdate: types.object({ onDelete: types.function([]) }),
        });
        this.orm = useService("orm");
        this.inputValue = signal("");
        this.inError = signal(false);
        this.popoverRef = useRef("tagsListPopoverRef");
        useListener(window, "click", (ev) => {
            if (!this.popoverRef.el?.contains(ev.target)) {
                this.discardTag();
            }
        });
    }

    onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        this.inError.set(false);
        if (hotkey === "enter") {
            this.updateTag();
        }
        if (hotkey === "escape") {
            this.discardTag();
        }
    }

    updateTag() {
        if (!this.isValidEmail) {
            this.inError.set(true);
            return;
        }
        this.props.onUpdateTag(this.inputValue());
        this.props.close();
    }

    discardTag() {
        this.props.tagToUpdate.onDelete();
        this.props.close();
    }

    get isValidEmail() {
        const value = parseEmail(this.inputValue());
        const name = value ? value[0] : "";
        return isEmail(name);
    }
}
