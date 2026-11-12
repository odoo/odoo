import { registry } from "@web/core/registry";
import { Component, onWillStart, proxy, useProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";

export class PosPaymentProviderCards extends Component {
    static template = "pos_payment_method.PosPaymentProviderCards";
    static components = {};
    props = useProps(standardWidgetProps);

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = proxy({
            allProviders: [],
            disabled: false,
        });

        onWillStart(async () => {
            this.state.allProviders = await this.orm.call(
                "pos.electronic.payment",
                "get_provider_status"
            );
        });
    }

    get providers() {
        return Object.entries(this.state.allProviders)
            .map(([provider, data]) => ({ provider, ...data }))
            .filter((p) => p.type === this.props.record.data.integration_type);
    }

    async installModule(moduleId) {
        this.state.disabled = true;
        await this.orm
            .call("ir.module.module", "button_immediate_install", [moduleId])
            .then(async (result) => {
                if (result) {
                    await this.props.record.discard();
                    window.location.reload();
                }
            })
            .finally(() => {
                this.state.disabled = false;
            });
    }

    setupProvider(provider) {
        this.props.record.update({
            payment_provider: provider.provider,
            name: provider.name,
        });
    }
}

export const PosPaymentProviderCardsParams = {
    component: PosPaymentProviderCards,
};

registry.category("view_widgets").add("pos_payment_provider_cards", PosPaymentProviderCardsParams);
