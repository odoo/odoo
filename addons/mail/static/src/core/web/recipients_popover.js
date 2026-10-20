import { PopoverCard } from "@mail/core/common/popover_card/popover_card";

import { ORM } from "@web/core/orm_plugin";

import { Component, onWillStart, signal, types, usePlugin, useProps } from "@odoo/owl";

/**
 * This popover is used to show a card with details for the recipients' partner with its name,
 * email and phone number. The card can also redirect the user to the `res.partner` form view if he
 * wants more details or edit said partner.
 */
export class RecipientsPopover extends Component {
    static template = "mail.RecipientsPopover";
    static components = { PopoverCard };

    setup() {
        this.props = useProps({
            close: types.function([]),
            email: types.string(),
            id: types.number(),
            name: types.string(),
            viewProfileBtnOverride: types.function([]),
        });
        this.orm = usePlugin(ORM);
        this.partner = signal(null);
        // Not awaited: the card shows name and email at once, the rest when it arrives.
        onWillStart(() => {
            this.orm
                .read("res.partner", [this.props.id], ["email_normalized", "phone"])
                .then(([partner]) => this.partner.set(partner));
        });
    }

    get email() {
        return this.partner()?.email_normalized || this.props.email;
    }

    get phone() {
        return this.partner()?.phone;
    }

    onClickViewProfile() {
        this.props.close();
        this.props.viewProfileBtnOverride();
    }
}
