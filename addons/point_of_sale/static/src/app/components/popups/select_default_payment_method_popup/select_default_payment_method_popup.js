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
                options: t.array(
                    t.object({ name: t.string(), label: t.string(), value: t.boolean() })
                ),
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
            options: Object.fromEntries(
                this.props.groups.map((group) => [
                    group.provider,
                    Object.fromEntries(group.options.map((option) => [option.name, option.value])),
                ])
            ),
        });
    }

    select(provider, pmId) {
        this.state.selection[provider] = pmId;
    }

    toggleOption(provider, name) {
        this.state.options[provider][name] = !this.state.options[provider][name];
    }

    confirmSelection() {
        this.props.getPayload({
            selection: { ...this.state.selection },
            options: Object.fromEntries(
                Object.entries(this.state.options).map(([provider, options]) => [
                    provider,
                    { ...options },
                ])
            ),
        });
        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}
