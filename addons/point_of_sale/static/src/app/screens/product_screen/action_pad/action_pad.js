import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component } from "@odoo/owl";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";
import { useService } from "@web/core/utils/hooks";
import { BackButton } from "@point_of_sale/app/screens/product_screen/action_pad/back_button/back_button";

export class ActionpadWidget extends Component {
    static template = "point_of_sale.ActionpadWidget";
    static components = { SelectPartnerButton, BackButton };
    static props = {
        partner: { type: [Object, { value: null }], optional: true },
        onClickMore: { type: Function, optional: true },
        actionName: String,
        actionToTrigger: Function,
        showActionButton: { type: Boolean, optional: true },
        fastValidate: { type: Function, optional: true },
    };
    static defaultProps = {
        showActionButton: true,
    };

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
    }

    get currentOrder() {
        return this.pos.getOrder();
    }

    get showFastPaymentMethods() {
        return (
            this.pos.config.is_fast_payment &&
            this.pos.config.fast_payment_method_ids?.length &&
            this.pos.router.state.current === "ProductScreen"
        );
    }
}
