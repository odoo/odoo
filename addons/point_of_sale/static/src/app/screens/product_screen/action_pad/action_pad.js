import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component, props, t } from "@odoo/owl";
import { SelectPartnerButton } from "@point_of_sale/app/screens/product_screen/control_buttons/select_partner_button/select_partner_button";
import { useService } from "@web/core/utils/hooks";
import { BackButton } from "@point_of_sale/app/screens/product_screen/action_pad/back_button/back_button";

export const actionpadWidgetProps = {
    order: t.object(),
    onClickMore: t.function().optional(),
    actionName: t.string(),
    actionToTrigger: t.function(),
    showActionButton: t.boolean().optional(true),
    fastValidate: t.function().optional(),
    buttonClasses: t.string().optional(""),
};

export class ActionpadWidget extends Component {
    static template = "point_of_sale.ActionpadWidget";
    static components = { SelectPartnerButton, BackButton };
    props = props(actionpadWidgetProps);

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
    }

    get currentOrder() {
        return this.props.order;
    }

    get partner() {
        return this.currentOrder.getPartner();
    }

    get showFastPaymentMethods() {
        return (
            this.pos.config.use_fast_payment &&
            this.pos.config.fast_payment_method_ids?.length &&
            this.pos.router.state.current === "ProductScreen"
        );
    }
}
