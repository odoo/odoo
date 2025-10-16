import { useState } from "@web/owl2/utils";
import { registry } from "@web/core/registry";
import { Component, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class PosPaymentProviderCards extends Component {
    static template = "point_of_sale.PosPaymentProviderCards";
    static components = {};
    static props = {
        ...standardWidgetProps,
        paymentMethodType: { validate: (pmt) => ["terminal", "external_qr"].includes(pmt) },
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
            const allProviders = await this.orm.call("pos.payment.method", "get_provider_status");
            this.state.providers = allProviders.filter(
                (p) => p.type === this.props.paymentMethodType
            );
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
                payment_provider: provider.provider,
                name: provider.name,
            });
        }
    }
}

export const PosPaymentProviderCardsParams = {
    component: PosPaymentProviderCards,
    extractProps: ({ options }) => ({ paymentMethodType: options.payment_method_type }),
};

registry.category("view_widgets").add("pos_payment_provider_cards", PosPaymentProviderCardsParams);
