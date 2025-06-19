import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart } from "@odoo/owl";

/**
 * This popover is used to show a card with details for the recipients' partner with its name,
 * email and phone number. The card can also redirect the user to the `res.partner` form view if he
 * wants more details or edit said partner.
 */
export class RecipientsPopover extends Component {
    static template = "mail.RecipientsPopover";
    static props = {
        id: { type: Number, required: true },
        close: { type: Function, required: true },
        viewProfileBtnOverride: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        onWillStart(async () => {
            [this.partner] = await this.orm.read("res.partner", [this.props.id], this.fieldNames);
        });
    }

    get name() {
        return this.partner.name || this.partner.display_name || _t("Unnamed");
    }

    get phone() {
        return this.partner.phone;
    }

    get email() {
        return this.partner.email_normalized || this.partner.email;
    }

    get fieldNames() {
        return ["name", "email_normalized", "email", "phone", "display_name"];
    }

    onClickViewProfile() {
        this.props.close();
        this.props.viewProfileBtnOverride();
    }
}
