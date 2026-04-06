import { onWillStart } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";

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

    isNewsletterPopup() {
        const selectors =
            "[data-snippet='s_newsletter_subscribe_popup'], [data-snippet='s_newsletter_benefits_popup']";
        return !!this.env.getEditingElement().closest(selectors);
    }
}
