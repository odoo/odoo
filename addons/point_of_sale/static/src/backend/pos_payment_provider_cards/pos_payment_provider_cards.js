import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class PosPaymentProviderCards extends Component {
    static template = "point_of_sale.PosPaymentProviderCards";
    static components = {};
    static props = {
        ...standardWidgetProps,
        paymentMethodTypes: { type: Array, optional: true },
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            providers: [],
            disabled: false,
        });

        onWillStart(async () => {
            const res = await this.orm.call("pos.payment.method", "get_provider_status", [
                providers.map((p) => p[1]),
            ]);

            this.state.providers = providers
                .filter(
                    (prov) =>
                        (!this.props.paymentMethodTypes ||
                            this.props.paymentMethodTypes.includes(prov[3])) &&
                        res.state.some((moduleState) => moduleState.name === prov[1])
                )
                .map((prov) => {
                    const status = res.state.find((p) => p.name === prov[1]);
                    return Object.assign(
                        {
                            selection: prov[0],
                            provider: prov[2],
                            payment_method_type: prov[3],
                        },
                        status
                    );
                });
        });
    }

    get config_ids() {
        return this.props.record.evalContext.context.config_ids;
    }

    async installModule(moduleId) {
        const recordSave = await this.props.record.save();
        if (!recordSave) {
            return;
        }
        this.state.disabled = true;
        await this.orm
            .call("ir.module.module", "button_immediate_install", [moduleId])
            .then((result) => {
                this.state.disabled = false;
                if (result) {
                    window.location.reload();
                }
            })
            .finally(() => {
                this.state.disabled = false;
            });
    }

    async setupProvider(moduleId) {
        const provider = this.state.providers.find((p) => p.id === moduleId);
        if (provider) {
            this.props.record.update({
                payment_method_type: provider.payment_method_type,
                use_payment_terminal: provider.selection,
                name: provider.provider,
            });
        }
    }
}

// Selection, module_name, friendly name, payment method type
const providers = [
    ["ingenico", "pos_iot_ingenico", "Ingenico", "terminal"],
    ["six_iot", "pos_iot_six", "SIX", "terminal"],
    ["adyen", "pos_adyen", "Adyen", "terminal"],
    ["mercado_pago", "pos_mercado_pago", "Mercado Pago", "terminal"],
    ["razorpay", "pos_razorpay", "Razorpay", "terminal"],
    ["stripe", "pos_stripe", "Stripe", "terminal"],
    ["viva_com", "pos_viva_com", "Viva.com", "terminal"],
    ["worldline", "pos_iot_worldline", "Worldline", "terminal"],
    ["tyro", "pos_tyro", "Tyro", "terminal"],
    ["pine_labs", "pos_pine_labs", "Pine Labs", "terminal"],
    ["qfpay", "pos_qfpay", "QFPay", "terminal"],
    ["payconiq", "pos_payconiq", "Payconiq", "external_qr"],
];

export const PosPaymentProviderCardsParams = {
    component: PosPaymentProviderCards,
    extractProps: ({ options }) => ({ paymentMethodTypes: options.payment_method_types }),
};

registry.category("view_widgets").add("pos_payment_provider_cards", PosPaymentProviderCardsParams);
