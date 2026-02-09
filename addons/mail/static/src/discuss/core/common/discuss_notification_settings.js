import { useState } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class DiscussNotificationSettings extends Component {
    static props = {};
    static template = "mail.DiscussNotificationSettings";

    setup() {
        this.store = useService("mail.store");
        this.state = useState({
            selectedDuration: false,
        });
    }

    onChangeMessageSound() {
        this.store.settings.messageSound = !this.store.settings.messageSound;
    }
}
