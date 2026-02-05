import { useLayoutEffect } from "@web/owl2/utils";
import { usePopover } from "@web/core/popover/popover_hook";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useBus, useChildRef, useService } from "@web/core/utils/hooks";
import { RecipientsInputTagsListPopover } from "./recipients_input_tags_list_popover";
import { RecipientsPopover } from "./recipients_popover";

import { Component, EventBus } from "@odoo/owl";

export class RecipientTag extends Component {
    static template = "mail.RecipientTag";
    static components = { BadgeTag };
    static props = [
        "bus",
        "color?",
        "email",
        "id",
        "name",
        "onClick?",
        "onDelete",
        "resId?",
        "text",
        "tooltip",
        "updateRecipient",
    ];

    setup() {
        this.ref = useChildRef();
        this.action = useService("action");

        this.recipientPopover = usePopover(RecipientsPopover, {
            position: "bottom-middle",
        });
        this.emailSetterPopover = usePopover(RecipientsInputTagsListPopover, {
            closeOnClickAway: false,
            position: "bottom-middle",
        });

        useBus(this.props.bus, "open", (ev) => {
            if (this.props.id === ev.detail.id) {
                this.emailSetterPopover.open(this.ref.el, {
                    tagToUpdate: {
                        email: this.props.email,
                        name: this.props.name,
                        onDelete: this.props.onDelete,
                    },
                    onUpdateTag: (newEmail) =>
                        this.props.updateRecipient(newEmail, this.props.resId),
                });
            }
        });
    }

    onClick(ev) {
        if (!this.props.resId || !this.props.email) {
            return;
        }
        const viewProfileBtnOverride = () => {
            const action = {
                type: "ir.actions.act_window",
                res_model: "res.partner",
                res_id: this.props.resId,
                views: [[false, "form"]],
                target: "current",
            };
            this.action.doAction(action);
        };
        this.recipientPopover.open(ev.target, {
            viewProfileBtnOverride,
            id: this.props.resId,
        });
    }
}

export function useRecipientChecker(getTags) {
    const bus = new EventBus();
    useLayoutEffect(
        (invalidTag) => {
            if (invalidTag) {
                bus.trigger("open", {
                    id: invalidTag.id,
                });
            }
        },
        () => [getTags().find((tag) => !tag.email)]
    );
    return bus;
}
