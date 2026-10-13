import { Component, proxy, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { PosPaymentMethod } from "@point_of_sale/app/models/pos_payment_method";

export class SelectDefaultPaymentMethodPopup extends Component {
    static template = "point_of_sale.SelectDefaultPaymentMethodPopup";
    static components = { Dialog };
    props = useProps({
        groups: t.array(
            t.object({
                provider: t.string(),
                name: t.string(),
                paymentMethods: t.array(t.instanceOf(PosPaymentMethod)),
                selectedId: t.or([t.number(), t.literal(false)]),
            })
        ),
        close: t.function(),
        getPayload: t.function(),
    });

    setup() {
        this.state = proxy({
            selection: Object.fromEntries(
                this.props.groups.map((group) => [group.provider, group.selectedId])
            ),
        });
    }

    select(provider, pmId) {
        this.state.selection[provider] = pmId;
    }

    confirmSelection() {
        this.props.getPayload({ ...this.state.selection });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
