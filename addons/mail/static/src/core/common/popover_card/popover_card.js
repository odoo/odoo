import { Component, t, useProps } from "@odoo/owl";

/**
 * Generic card used as the root of popovers such as AvatarCard or
 * RecipientsPopover: provides the card background/border/sizing style,
 * leaving the content itself to the caller.
 */
export class PopoverCard extends Component {
    static template = "mail.PopoverCard";

    props = useProps({
        class: t.string().optional(),
        slots: t.object({
            default: t.any(),
            header: t.any().optional(),
        }),
    });
}
