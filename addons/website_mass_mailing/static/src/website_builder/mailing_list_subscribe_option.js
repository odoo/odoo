import { onWillStart } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class MailingListSubscribeOption extends BaseOptionComponent {
    static template = "website_mass_mailing.MailingListSubscribeOption";
    static props = {
        fetchMailingLists: Function,
    };

    setup() {
        super.setup();
        this.mailingLists = [];
        onWillStart(async () => {
            this.mailingLists = await this.props.fetchMailingLists();
        });
    }
}
