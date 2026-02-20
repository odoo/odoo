import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class PosPaymentProviderCards extends Component {
    static template = "point_of_sale.PosPaymentProviderCards";
    static components = {};
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            providers: [],
            type: this.props.record.data.payment_method_type,
            disabled: false,
        });

        onWillStart(async () => {
            const res = await this.orm.call("pos.payment.method", "get_provider_status", [
                providers.map((p) => p.module),
            ]);

            this.state.providers = providers
                .filter(
                    (prov) =>
                        res.state.some((moduleState) => moduleState.name === prov.module) &&
                        prov.type === this.state.type
                )
                .map((prov) => {
                    const status = res.state.find((p) => p.name === prov.module);
                    return Object.assign(
                        {
                            selection: prov.selection,
                            provider: prov.name,
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
                payment_method_type: this.state.type,
                use_payment_terminal: provider.selection,
                name: provider.provider,
            });
        }
    }
}

// prettier-ignore
/** @type {{ type: "terminal" | "cash_machine", selection: string, module: string, name: string }} */
const providers = [
    { type: "terminal", selection: "axepta_bnpp", module: "pos_iot_worldline", name: "Axepta BNP Paribas" },
    { type: "terminal", selection: "six_iot", module: "pos_iot_six", name: "SIX" },
    { type: "terminal", selection: "adyen", module: "pos_adyen", name: "Adyen" },
    { type: "terminal", selection: "mercado_pago", module: "pos_mercado_pago", name: "Mercado Pago" },
    { type: "terminal", selection: "razorpay", module: "pos_razorpay", name: "Razorpay" },
    { type: "terminal", selection: "stripe", module: "pos_stripe", name: "Stripe" },
    { type: "terminal", selection: "viva_com", module: "pos_viva_com", name: "Viva.com" },
    { type: "terminal", selection: "worldline", module: "pos_iot_worldline", name: "Worldline" },
    { type: "terminal", selection: "tyro", module: "pos_tyro", name: "Tyro" },
    { type: "terminal", selection: "pine_labs", module: "pos_pine_labs", name: "Pine Labs" },
    { type: "terminal", selection: "qfpay", module: "pos_qfpay", name: "QFPay" },
    { type: "terminal", selection: "dpopay", module: "pos_dpopay", name: "DPO Pay" },
    { type: "terminal", selection: "mollie", module: "pos_mollie", name: "Mollie" },
    { type: "cash_machine", selection: "glory", module: "pos_glory_cash", name: "Glory" },
];

export const PosPaymentProviderCardsParams = {
    component: PosPaymentProviderCards,
};

registry.category("view_widgets").add("pos_payment_provider_cards", PosPaymentProviderCardsParams);
