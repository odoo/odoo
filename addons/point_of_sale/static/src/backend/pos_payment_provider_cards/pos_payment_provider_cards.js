/** @odoo-module native */
import { Component, onWillStart, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets";
const log = makeLogger("pos.backend.payment_providers");
export class PosPaymentProviderCards extends Component {
    static template = "point_of_sale.PosPaymentProviderCards";
    static props = {
        ...standardWidgetProps,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            providers: [],
            disabled: false,
        });

        onWillStart(async () => {
            const res = await log.measure("get_provider_status", () =>
                this.orm.call("pos.payment.method", "get_provider_status", [
                    providers.map((p) => p[1]),
                ]),
            );
            log.logic("provider status", () => ({
                asked: providers.length,
                known: res.state.length,
            }));

            const statusByModule = new Map(
                res.state.map((status) => [status.name, status]),
            );
            this.state.providers = providers.flatMap(
                ([selection, moduleName, provider]) => {
                    const status = statusByModule.get(moduleName);
                    return status ? [{ ...status, selection, provider }] : [];
                },
            );
        });
    }

    async installModule(moduleId) {
        if (this.state.disabled) {
            log.logic("installModule: already pending", () => ({ moduleId }));
            return;
        }
        this.state.disabled = true;
        let reloading = false;
        try {
            const recordSave = await this.props.record.save();
            log.pipeline("installModule", () => ({ moduleId, recordSave }));
            if (!recordSave) {
                return;
            }
            const result = await this.orm.call(
                "ir.module.module",
                "button_immediate_install",
                [moduleId],
            );
            if (result) {
                browser.location.reload();
                reloading = true;
            }
        } finally {
            this.state.disabled = reloading;
        }
    }

    async setupProvider(moduleId) {
        const provider = this.state.providers.find((p) => p.id === moduleId);
        log.logic("setupProvider", () => ({
            moduleId,
            selection: provider?.selection,
        }));
        if (provider?.state === "installed" && !this.state.disabled) {
            await this.props.record.update({
                payment_method_type: "terminal",
                use_payment_terminal: provider.selection,
                name: provider.provider,
            });
        }
    }
}

const providers = [
    ["ingenico", "pos_iot_ingenico", "Ingenico"],
    ["six_iot", "pos_iot_six", "SIX"],
    ["adyen", "pos_adyen", "Adyen"],
    ["mercado_pago", "pos_mercado_pago", "Mercado Pago"],
    ["razorpay", "pos_razorpay", "Razorpay"],
    ["stripe", "pos_stripe", "Stripe"],
    ["viva_com", "pos_viva_com", "Viva.com"],
    ["worldline", "pos_iot_worldline", "Worldline"],
    ["tyro", "pos_tyro", "Tyro"],
    ["pine_labs", "pos_pine_labs", "Pine Labs"],
    ["qfpay", "pos_qfpay", "QFPay"],
    ["dpopay", "pos_dpopay", "DPO Pay"],
    ["mollie", "pos_mollie", "Mollie"],
];

export const PosPaymentProviderCardsParams = {
    component: PosPaymentProviderCards,
};

registry
    .category("view_widgets")
    .add("pos_payment_provider_cards", PosPaymentProviderCardsParams);
