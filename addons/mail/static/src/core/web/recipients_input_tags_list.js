import { onWillUpdateProps, toRaw, useEffect, useRef, useState } from "@odoo/owl";
import { TagsList } from "@web/components/tags_list/tags_list";
import { usePopover } from "@web/ui/popover/popover_hook";

import { RecipientsInputTagsListPopover } from "./recipients_input_tags_list_popover";

/**
 * Override of the TagsList so that the email address of each recipients can be checked.
 * If a recipient doesn't have an email address set to its partner a popover is opened below the corresponding
 * Tag.
 */
export class RecipientsInputTagsList extends TagsList {
    static template = "web.RecipientsInputTagsList";
    static props = {
        ...TagsList.props,
        updateRecipient: { type: Function, optional: true },
    };
    static defaultProps = { ...TagsList.defaultProps, updateRecipient: () => {} };
    setup() {
        this.popover = usePopover(RecipientsInputTagsListPopover, {
            closeOnClickAway: false,
            position: "bottom-middle",
        });
        this.tagToUpdateRef = useRef("tagToUpdate");
        this.state = useState({
            tagToUpdate: this.getFirstTagToUpdate(this.props.tags),
        });
        onWillUpdateProps((nextProps) => {
            this.state.tagToUpdate = this.getFirstTagToUpdate(nextProps.tags);
        });
        useEffect(
            () => {
                if (this.state.tagToUpdate && this.tagToUpdateRef.el) {
                    this.updateTag();
                } else if (this.popover.isOpen) {
                    this.popover.close();
                }
            },
            () => [this.state.tagToUpdate, this.tagToUpdateRef.el],
        );
    }

    getFirstTagToUpdate(tags) {
        for (const tag of tags) {
            if (!tag.email) {
                return tag;
            }
        }
    }

    tagEquals(tag1, tag2) {
        return toRaw(tag1) === toRaw(tag2);
    }

    updateTag() {
        this.popover.open(this.tagToUpdateRef.el, {
            tagToUpdate: this.state.tagToUpdate,
            onUpdateTag: (newEmail) =>
                this.props.updateRecipient(newEmail, this.state.tagToUpdate.resId),
        });
    }
}
