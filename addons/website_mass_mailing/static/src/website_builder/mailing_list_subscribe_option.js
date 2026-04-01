import { onWillStart } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class MailingListSubscribeOption extends BaseOptionComponent {
    static template = "website_mass_mailing.MailingListSubscribeOption";
    static dependencies = ["mailingListSubscribeOption"];

    setup() {
        super.setup();
        this.mailingLists = [];
        const { fetchMailingLists } = this.dependencies.mailingListSubscribeOption;
        onWillStart(async () => {
            this.mailingLists = await fetchMailingLists();
        });
    }
}
