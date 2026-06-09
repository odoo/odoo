import { Component, useEffect, useProps, signal } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class CarrierRatesLoader extends Component {
    static template = "delivery.carrier_rates_loader";

    props = useProps();
    showButton = signal(true);

    setup() {
        this.ormService = useService("orm");
        this.lastWeight = this.props.record.data.total_weight;

        // display the button if the weight changes
        useEffect(
            () => {
                const currWeight = this.props.record.data.total_weight;
                if (currWeight !== this.lastWeight) {
                    this.showButton.set(true);
                    this.lastWeight = currWeight;
                }
            }
        )
    }

    async loadCarrierRates() {
        // save to get the resId for the wizard
        if (!this.props.record.resId && this.props.record.save) {
            await this.props.record.save();
        }

        const wizardId = this.props.record.resId;
        const carrierIds = this.props.record.data.available_carrier_ids._currentIds || [];
        if (!wizardId || !carrierIds.length) {
            return;
        }

        try {
            await this.props.record.update({ is_loading_prices: true });

            // Make asynchronous calls to calculate the delivery rate for each carrier
            const ratePromises = carrierIds.map(async (carrierId) => {
                const result = await this.ormService.call(
                    "choose.delivery.carrier",
                    "get_wizard_carrier_rate",
                    [wizardId, carrierId]
                );
                return { carrierId, result };
            });

            const rates = await Promise.all(ratePromises);
            const carrierPrices = {};
            for (const rate of rates) {
                carrierPrices[rate.carrierId] = rate.result;
            }

            await this.props.record.update({
                carrier_prices: carrierPrices,
                carrier_prices_dumped: JSON.stringify(carrierPrices),
            });
        } finally {
            await this.props.record.update({ is_loading_prices: false });
            this.showButton.set(false);

            // reopen the carrier list after a short delay
            setTimeout(() => {
                const carrierInput = document.querySelector('div[name="carrier_id"] input');
                if (carrierInput) {
                    carrierInput.click();
                    carrierInput.dispatchEvent(new InputEvent("change", { bubbles: true }));
                    carrierInput.focus();
                }
            }, 100);
        }
    }
}

registry.category("view_widgets").add("delivery_carrier_rates_loader", {
    component: CarrierRatesLoader,
});
