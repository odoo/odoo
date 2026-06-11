import { Component, signal } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";

export class SubscriptionDialog extends Component {
    static template = "mysubscription.SubscriptionDialog";
    static components = { Dialog };

    setup() {
        this.subscription = useService("enterprise_subscription");
        this.code = signal("");
    }

    async onSubmit() {
        if (!this.code()) {
            return;
        }

        await this.subscription.submitCode(this.code());

        if (this.subscription.lastRequestStatus === "success") {
            this.props.close();
        } else {
            console.error("Not a success");
        }
    }
}
