import { BaseOptionComponent } from "@html_builder/core/utils";
import { useState } from "@odoo/owl";
import { useBus } from "@web/core/utils/hooks";

export class SupportedPaymentMethodsOption extends BaseOptionComponent {
    static template = "website_payment.SupportedPaymentMethodsOption";
    static props = {
        getMaxLimit: Function,
    };

    setup() {
        super.setup();
        this.state = useState({ maxLimit: Infinity });
        useBus(this.env.editorBus, "DOM_UPDATED", this.updateState.bind(this));
    }

    async updateState() {
        this.state.maxLimit = await this.props.getMaxLimit();
    }
}
