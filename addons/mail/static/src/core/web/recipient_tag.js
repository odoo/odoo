import { useHover } from "@mail/utils/common/hooks";

import { usePopover } from "@web/core/popover/popover_hook";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { OPEN_DELAY } from "@web/core/tooltip/tooltip_plugin";
import { useBus, useService } from "@web/core/utils/hooks";
import { RecipientsInputTagsListPopover } from "./recipients_input_tags_list_popover";
import { RecipientsPopover } from "./recipients_popover";

import {
    Component,
    EventBus,
    onMounted,
    onPatched,
    onWillUnmount,
    signal,
    types,
    useProps,
} from "@odoo/owl";

export class RecipientTag extends Component {
    static template = "mail.RecipientTag";
    static components = { BadgeTag };

    setup() {
        this.props = useProps({
            bus: types.instanceOf(EventBus),
            color: types.string().optional(),
            email: types.string(),
            id: types.string(),
            name: types.string(),
            onDelete: types.function([]).optional(),
            resId: types.or([types.number(), types.literal(false)]).optional(),
            text: types.string(),
            tooltip: types.string(),
            updateRecipient: types.function([types.string(), types.number()]),
        });
        this.ref = signal.ref();
        this.action = useService("action");

        const recipientPopoverRef = signal.ref();
        this.recipientPopover = usePopover(RecipientsPopover, {
            position: "bottom-middle",
            ref: recipientPopoverRef,
            setActiveElement: false,
        });
        // Delayed like a tooltip, so that crossing the tag does not open the card.
        let openTimeout;
        const hover = useHover([this.ref, recipientPopoverRef], {
            onHover: () => {
                clearTimeout(openTimeout);
                openTimeout = setTimeout(() => {
                    // `onAway` only clears the timeout 100 ms after leaving.
                    if (hover.isHover) {
                        this.openAvatarCard();
                    }
                }, OPEN_DELAY);
            },
            onAway: () => {
                clearTimeout(openTimeout);
                this.recipientPopover.close();
            },
            stateObserver: () => [recipientPopoverRef()],
        });
        onWillUnmount(() => clearTimeout(openTimeout));
        this.emailSetterPopover = usePopover(RecipientsInputTagsListPopover, {
            closeOnClickAway: false,
            position: "bottom-middle",
        });

        useBus(this.props.bus, "open", (ev) => {
            if (this.props.id === ev.detail.id) {
                this.emailSetterPopover.open(this.ref(), {
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

    get hasAvatarCard() {
        return Boolean(this.props.resId && this.props.email);
    }

    openAvatarCard() {
        if (!this.hasAvatarCard || this.recipientPopover.isOpen) {
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
        this.recipientPopover.open(this.ref(), {
            viewProfileBtnOverride,
            email: this.props.email,
            id: this.props.resId,
            name: this.props.name,
        });
    }
}

/**
 * @param {() => {id: string, email: string}[]} getTags
 * @returns {EventBus}
 */
export function useRecipientChecker(getTags) {
    const bus = new EventBus();
    let invalidTag;
    // after the patch: the tag of the invalid recipient has to be mounted to open its popover
    const checkRecipients = () => {
        const tag = getTags().find((tag) => !tag.email);
        if (tag === invalidTag) {
            return;
        }
        invalidTag = tag;
        if (tag) {
            bus.trigger("open", { id: tag.id });
        }
    };
    onMounted(checkRecipients);
    onPatched(checkRecipients);
    return bus;
}
