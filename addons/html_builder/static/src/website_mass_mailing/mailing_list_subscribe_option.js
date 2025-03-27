import { onWillStart } from "@odoo/owl";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class MailingListSubscribeOption extends BaseOptionComponent {
    static template = "html_builder.MailingListSubscribeOption";
    static props = {
        fetchMailingLists: Function,
    };

    setup() {
        this.mailingLists = [];
        onWillStart(async () => {
            this.mailingLists = await this.props.fetchMailingLists();
        });
    }
}
